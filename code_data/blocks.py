"""
Decodes the linear list of instructions into a sequence of blocks.
Every instruction that is jumped to starts a new block.
"""

from __future__ import annotations

import ctypes
import dis
import sys
from dataclasses import replace
from typing import Iterable, Tuple

from . import (
    AdditionalConstant,
    AdditionalConstants,
    AdditionalName,
    AdditionalNames,
    AdditionalVarname,
    AdditionalVarnames,
    Arg,
    Args,
    Blocks,
    BlockType,
    Cellvar,
    Constant,
    ConstantValue,
    Freevar,
    Instruction,
    Jump,
    Name,
    Varname,
)
from .line_mapping import LineMapping


def bytes_to_blocks(
    b: bytes,
    line_mapping: LineMapping,
    names: tuple[str, ...],
    varnames: tuple[str, ...],
    freevars: tuple[str, ...],
    cellvars: tuple[str, ...],
    constants: tuple[ConstantValue, ...],
    block_type: BlockType,
    args: Args,
) -> tuple[Blocks, AdditionalNames, AdditionalVarnames, AdditionalConstants]:
    """
    Parse a sequence of bytes as a sequence of blocks of instructions.
    """
    from . import FunctionBlock

    # First, iterate through bytes to make instructions while also making set of all the
    # targets
    # List of bytecode offsets and instructions
    offsets_and_instruction: list[tuple[int, Instruction]] = []
    # Set of all instruction offsets which are targets of jump blocks
    # The targets always includes the first block
    targets_set = {0}

    # For recording what names we have found to understand the order of the names
    found_names: list[str] = []

    # We count all the arg names as "found", since we will always preserve them in the
    # args
    found_varnames: list[str] = list(args.parameters.keys())

    found_cellvars: list[str] = []

    # For recording what constants we have found to understand the order of the
    # constants
    found_constants: list[ConstantValue] = []
    # Keep a set of the constant indices we have found, so we can check this against
    # our initial constants at the end to see which we still have to add
    # We should do the same with names, but checking against found_names works
    # fine as long as names aren't duplicated, which they don't seem to be in the
    # same way as constants
    found_constant_indices: set[int] = set()

    # If we have a function block and a docstring, the first constant is the docstring.
    if isinstance(block_type, FunctionBlock) and block_type.docstring is not None:
        found_constants.append(block_type.docstring)
        found_constant_indices.add(0)

    for opcode, arg, n_args, offset, next_offset in _parse_bytes(b):

        # Compute the jump targets, initially with just the byte offset
        # Once we know all the block targets, we will transform to be block offsets
        processed_arg = to_arg(
            opcode,
            arg,
            next_offset,
            names,
            found_names,
            varnames,
            found_varnames,
            freevars,
            cellvars,
            found_cellvars,
            constants,
            found_constants,
            found_constant_indices,
        )
        if isinstance(processed_arg, Jump):
            targets_set.add(processed_arg.target)
            # Store the number of args if this is a jump instruction
            # This is needed to preserve isomporphic behavior. Otherwise
            # there are cases where jump instructions could be different values
            # (and have different number of args), but point to the same instruction
            # offset.
            n_args_override = n_args if n_args > 1 else None
        else:
            n_args_override = None

        instruction = Instruction(
            name=dis.opname[opcode],
            arg=processed_arg,
            _n_args_override=n_args_override,
            line_number=line_mapping.offset_to_line.pop(offset),
            _line_offsets_override=tuple(
                line_mapping.offset_to_additional_line_offsets.pop(offset, [])
            ),
        )
        offsets_and_instruction.append((offset, instruction))

        # Pop all additional line offsets for additional args
        for i in range(offset + 2, next_offset, 2):
            line_mapping.offset_to_line.pop(i)
            line_mapping.offset_to_additional_line_offsets.pop(i, None)

    # Compute a sorted list of target, to map each one to a bloc offset
    targets = sorted(targets_set)
    del targets_set
    # Then, iterate through each instruction to update the jump to point to the
    # block offset, instead of the bytecode offset
    block: list[Instruction]
    blocks: list[list[Instruction]] = []
    for offset, instruction in offsets_and_instruction:
        # If the instruction offset is one of the targets, start a new block
        if offset in targets:
            block = []
            blocks.append(block)
        # If the instruction is a jump instruction, update it's arg with the
        # block offset, instead of instruction offset
        if isinstance(instruction.arg, Jump):
            instruction = replace(
                instruction,
                arg=replace(
                    instruction.arg,
                    target=targets.index(instruction.arg.target),
                ),
            )
        block.append(instruction)

    additional_names = tuple(
        AdditionalName(name, i)
        for i, name in enumerate(names)
        if name not in found_names
    )
    additional_varnames = tuple(
        AdditionalVarname(name, i)
        for i, name in enumerate(varnames)
        if name not in found_varnames
    )
    additional_constants = tuple(
        AdditionalConstant(constant, i)
        for i, constant in enumerate(constants)
        if i not in found_constant_indices
    )
    return (
        tuple(tuple(instruction for instruction in block) for block in blocks),
        additional_names,
        additional_varnames,
        additional_constants,
    )


def blocks_to_bytes(
    blocks: Blocks,
    additional_names: AdditionalNames,
    additional_varnames: AdditionalVarnames,
    additional_consts: AdditionalConstants,
    freevars: tuple[str, ...],
    block_type: BlockType,
) -> Tuple[
    bytes,
    LineMapping,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[ConstantValue, ...],
]:
    from . import FunctionBlock

    # First compute mapping from block to offset
    changed_instruction_lengths = True
    # So that we know the bytecode offsets for jumps when iterating though instructions
    block_index_to_instruction_offset: dict[int, int] = {}

    # Mapping of block index, instruction index, to integer arg values
    args: dict[tuple[int, int], int] = {}

    # List of names we have collected from the instructions
    names: list[str] = []
    # Mapping of name index to final name positions
    name_final_positions: dict[int, int] = {}

    varnames: list[str] = list(
        block_type.args.parameters.keys()
        if isinstance(block_type, FunctionBlock)
        else ()
    )
    varname_final_positions: dict[int, int] = {i: i for i in range(len(varnames))}

    cellvars: list[str] = []
    cellvar_final_positions: dict[int, int] = {}

    # List of constants we have collected from the instructions
    constants: list[ConstantValue] = []
    # Mapping of constant index to constant name positions
    constant_final_positions: dict[int, int] = {}

    # If it is a function block, we start with the docstring
    if isinstance(block_type, FunctionBlock) and block_type.docstring is not None:
        constants.append(block_type.docstring)
        constant_final_positions[0] = 0

    # Iterate through all blocks and change jump instructions to offsets
    while changed_instruction_lengths:

        current_instruction_offset = 0
        # First go through and update all the instruction blocks
        for block_index, block in enumerate(blocks):
            block_index_to_instruction_offset[block_index] = current_instruction_offset
            for instruction_index, instruction in enumerate(block):
                if (block_index, instruction_index) in args:
                    arg_value = args[block_index, instruction_index]
                else:
                    arg_value = from_arg(
                        instruction.arg,
                        block_type,
                        names,
                        name_final_positions,
                        varnames,
                        varname_final_positions,
                        freevars,
                        cellvars,
                        cellvar_final_positions,
                        constants,
                        constant_final_positions,
                    )
                    args[block_index, instruction_index] = arg_value
                n_instructions = instruction._n_args_override or _instrsize(arg_value)
                current_instruction_offset += n_instructions
        # Then go and update all the jump instructions. If any of them
        # change the number of instructions needed for the arg, repeat
        changed_instruction_lengths = False
        current_instruction_offset = 0
        for block_index, block in enumerate(blocks):
            for instruction_index, instruction in enumerate(block):
                arg = instruction.arg
                arg_value = args[block_index, instruction_index]
                n_instructions = instruction._n_args_override or _instrsize(arg_value)
                current_instruction_offset += n_instructions

                if isinstance(arg, Jump):
                    target_instruction_offset = block_index_to_instruction_offset[
                        arg.target
                    ]
                    multiplier = 1 if _ATLEAST_310 else 2
                    if arg.relative:
                        new_arg_value = (
                            target_instruction_offset - current_instruction_offset
                        ) * multiplier
                    else:
                        new_arg_value = multiplier * target_instruction_offset
                    # If we aren't overriding and the new size of instructions is not
                    # the same as the old, mark this as updated, so we re-calculate
                    # block positions!
                    if (
                        not instruction._n_args_override
                        and n_instructions != _instrsize(new_arg_value)
                    ):
                        changed_instruction_lengths = True
                    args[block_index, instruction_index] = new_arg_value
    # Add additional names to the names and add final positions
    for additional_name in additional_names:
        i, name = additional_name.index, additional_name.name
        names.append(name)
        name_final_positions[i] = len(names) - 1
    # Sort positions by final position
    names = [
        names[i] for _, i in sorted(name_final_positions.items(), key=lambda x: x[0])
    ]

    for additional_varname in additional_varnames:
        i, name = additional_varname.index, additional_varname.varname
        varnames.append(name)
        varname_final_positions[i] = len(varnames) - 1
    varnames = [
        varnames[i]
        for _, i in sorted(varname_final_positions.items(), key=lambda x: x[0])
    ]

    cellvars = [
        cellvars[i]
        for _, i in sorted(cellvar_final_positions.items(), key=lambda x: x[0])
    ]

    # Now that we know the total number of cellvars, incremement all the freevar
    # indices by the number of cellvars, for each arg
    for block_index, block in enumerate(blocks):
        for instruction_index, instruction in enumerate(block):
            arg = instruction.arg
            if isinstance(arg, Freevar):
                args[block_index, instruction_index] += len(cellvars)

    # Add additional consts to the constants and add final positions
    for additional_constant in additional_consts:
        i, constant = additional_constant.index, additional_constant.constant
        constants.append(constant)
        constant_final_positions[i] = len(constants) - 1

    # Sort positions by final position
    constants = [
        constants[i]
        for _, i in sorted(constant_final_positions.items(), key=lambda x: x[0])
    ]

    # Finally go assemble the bytes and the line mapping
    bytes_: list[int] = []
    line_mapping = LineMapping()
    for block_index, block in enumerate(blocks):
        for instruction_index, instruction in enumerate(block):
            offset = len(bytes_)

            line_mapping.offset_to_line[offset] = instruction.line_number
            if instruction._line_offsets_override:
                line_mapping.offset_to_additional_line_offsets[offset] = list(
                    instruction._line_offsets_override
                )

            arg_value = args[block_index, instruction_index]
            n_args = instruction._n_args_override or _instrsize(arg_value)
            # Duplicate semantics of write_op_arg
            # to produce the the right number of extended arguments
            # https://github.com/python/cpython/blob/b2e5794870eb4728ddfaafc0f79a40299576434f/Python/wordcode_helpers.h#L22-L44
            for i in reversed(range(n_args)):
                bytes_.append(
                    dis.opmap[instruction.name] if i == 0 else dis.EXTENDED_ARG
                )
                bytes_.append((arg_value >> (8 * i)) & 0xFF)

    return (
        bytes(bytes_),
        line_mapping,
        tuple(names),
        tuple(varnames),
        tuple(cellvars),
        tuple(constants),
    )


def to_arg(
    opcode: int,
    arg: int,
    next_offset: int,
    names: tuple[str, ...],
    found_names: list[str],
    varnames: tuple[str, ...],
    found_varnames: list[str],
    freevars: tuple[str, ...],
    cellvars: tuple[str, ...],
    found_cellvars: list[str],
    consts: tuple[ConstantValue, ...],
    found_constants: list[ConstantValue],
    found_constant_indices: set[int],
) -> Arg:
    if opcode in dis.hasjabs:
        return Jump((2 if _ATLEAST_310 else 1) * arg, False)
    elif opcode in dis.hasjrel:
        return Jump(next_offset + ((2 if _ATLEAST_310 else 1) * arg), True)
    elif opcode in dis.hasname:
        name = names[arg]
        # Check if its the proper position
        if name not in found_names:
            found_names.append(name)
        wrong_position = found_names.index(name) != arg
        return Name(name, arg if wrong_position else None)
    elif opcode in dis.haslocal:
        varname = varnames[arg]
        # Check if its the proper position
        if varname not in found_varnames:
            found_varnames.append(varname)
        wrong_position = found_varnames.index(varname) != arg
        return Varname(varname, arg if wrong_position else None)
    elif opcode in dis.hasfree:
        # The cell vars are indexed first then the freevars.
        is_cellvar = arg < len(cellvars)
        if is_cellvar:
            cellvar = cellvars[arg]
            # Check if its the proper position
            if cellvar not in found_cellvars:
                found_cellvars.append(cellvar)
            wrong_position = found_cellvars.index(cellvar) != arg
            return Cellvar(cellvar, arg if wrong_position else None)
        # Index into freevars with remaining arg
        return Freevar(freevars[arg - len(cellvars)])
    elif opcode in dis.hasconst:
        found_constant_indices.add(arg)
        constant = consts[arg]
        if constant not in found_constants:
            found_constants.append(constant)
        wrong_position = found_constants.index(constant) != arg
        return Constant(constant, arg if wrong_position else None)
    return arg


def from_arg(
    arg: Arg,
    block_type: BlockType,
    names: list[str],
    name_final_positions: dict[int, int],
    varnames: list[str],
    varnames_final_positions: dict[int, int],
    freevars: tuple[str, ...],
    cellvars: list[str],
    cellvars_final_positions: dict[int, int],
    constants: list[ConstantValue],
    constants_final_positions: dict[int, int],
) -> int:
    from . import FunctionBlock

    # Use 1 as the arg_value, which will be update later
    if isinstance(arg, Jump):
        return 1
    if isinstance(arg, Name):
        if arg.name not in names:
            names.append(arg.name)
        index = names.index(arg.name)
        final_index = index if arg._index_override is None else arg._index_override
        name_final_positions[final_index] = index
        return final_index
    if isinstance(arg, Varname):
        if arg.varname not in varnames:
            varnames.append(arg.varname)
        index = varnames.index(arg.varname)
        final_index = index if arg._index_override is None else arg._index_override
        varnames_final_positions[final_index] = index
        return final_index
    if isinstance(arg, Freevar):
        return freevars.index(arg.freevar)
    if isinstance(arg, Cellvar):
        if arg.cellvar not in cellvars:
            cellvars.append(arg.cellvar)
        index = cellvars.index(arg.cellvar)
        final_index = index if arg._index_override is None else arg._index_override
        cellvars_final_positions[final_index] = index
        return final_index
    if isinstance(arg, Constant):

        # If this is the first index, and we have a docstring which is None,
        # and this value is a string, prepend a None instead of a string
        # so that this value is not used as a docstring.
        # This is needed to preserve the behavior for functions which don't have
        # a docstring after normalizing, otherwise, we would eliminate the None
        # const, because it is unused, and then fail to re-add it.
        # We also don't want to uncoditionally use the docstring as the first argument,
        # because list comprehensions don't do this.
        docstring_is_none = (
            isinstance(block_type, FunctionBlock) and block_type.docstring is None
        )
        first_const = not constants
        arg_is_string = isinstance(arg.value, str)
        no_override = arg._index_override is None
        if docstring_is_none and first_const and arg_is_string and no_override:
            constants.append(None)
            constants_final_positions[0] = 0

        if arg.value not in constants:
            constants.append(arg.value)
        index = constants.index(arg.value)
        final_index = index if arg._index_override is None else arg._index_override
        constants_final_positions[final_index] = index
        return final_index
    return arg


def verify_block(blocks: Blocks) -> None:
    """
    Verify that the blocks are valid, by making sure every
    instruction that jumps can find it's block.
    """
    for block in blocks:
        assert block, "Block is empty"
        for instruction in block:
            arg = instruction.arg
            if isinstance(arg, Jump):
                assert arg.target in range(len(blocks)), "Jump target is out of range"


# TODO: Possibly replace all these with `_additional_args` and use the args?

# Bytecode instructions jumps refer to the instruction offset, instead of byte
# offset in Python >= 3.10 due to this PR https://github.com/python/cpython/pull/25069
_ATLEAST_310 = sys.version_info >= (3, 10)


def _parse_bytes(b: bytes) -> Iterable[tuple[int, int, int, int, int]]:
    """
    Parses a sequence of bytes as instructions.

    For each it return returns a tuple of:

    1. The instruction opcode
    2. the instruction argument
    3. The number of args this instruction used
    4. The first offset of this instruction
    5. The first offset after this instruction
    """
    n_args: int = 0
    arg: int = 0
    for i in range(0, len(b), 2):
        opcode = b[i]
        arg |= b[i + 1]
        n_args += 1
        if opcode == dis.EXTENDED_ARG:
            arg = arg << 8
            # https://github.com/python/cpython/pull/31285
            if arg > _c_int_upper_limit:
                arg -= _c_int_length
        else:
            first_offset = i - ((n_args - 1) * 2)
            next_offset = i + 2
            yield (opcode, arg, n_args, first_offset, next_offset)
            n_args = 0
            arg = 0


def _instrsize(arg: int) -> int:
    """
    Minimum number of code units necessary to encode instruction with
    EXTENDED_ARGs

    From https://github.com/python/cpython/blob/b2e5794870eb4728ddfaafc0f79a40299576434f/Python/wordcode_helpers.h#L11-L20 # noqa: E501
    """
    # Negative args need to wrap
    # https://github.com/python/cpython/issues/90880
    if arg < 0:
        return 4
    return 1 if arg <= 0xFF else 2 if arg <= 0xFFFF else 3 if arg <= 0xFFFFFF else 4


# The number of bits in a signed int
_c_int_bit_size = ctypes.sizeof(ctypes.c_int()) * 8
# The maximum value that can be stored in a signed int
_c_int_upper_limit = (2 ** (_c_int_bit_size - 1)) - 1
# The number of values that can be stored in a signed int
_c_int_length = 2**_c_int_bit_size
