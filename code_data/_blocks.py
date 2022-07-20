"""
Decodes the linear list of instructions into a sequence of blocks.
Every instruction that is jumped to starts a new block.
"""

from __future__ import annotations

import ctypes
import dis
import sys
from dataclasses import dataclass, field, replace
from typing import Generic, Iterable, Optional, Tuple, TypeVar

from opcode import HAVE_ARGUMENT

from . import (
    AdditionalArgs,
    Arg,
    Args,
    Blocks,
    BlockType,
    Cellvar,
    Constant,
    ConstantValue,
    Freevar,
    FunctionBlock,
    Instruction,
    Jump,
    Name,
    NoArg,
    Varname,
)
from ._line_mapping import LineMapping


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
) -> tuple[Blocks, AdditionalArgs]:
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

    # Record each type of arg, as we find it, so we know which ones are missing at the
    # end and which are in the wrong order
    found_names = ToArgs(names)
    # We count all the arg names as "found", since we will always preserve them in the
    # args
    found_varnames = ToArgs(varnames, {i: i for i in range(len(args.parameters))})
    found_cellvars = ToArgs(cellvars)
    found_constants = ToArgs(constants)

    # If we have a function block and a docstring, the first constant is the docstring.
    if isinstance(block_type, FunctionBlock) and block_type.docstring is not None:
        found_constants.found_index(0)

    for opcode, arg, n_args, offset, next_offset in _parse_bytes(b):

        # Compute the jump targets, initially with just the byte offset
        # Once we know all the block targets, we will transform to be block offsets
        processed_arg = to_arg(
            opcode,
            arg,
            next_offset,
            found_names,
            found_varnames,
            freevars,
            found_cellvars,
            found_constants,
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
            line_mapping.offset_to_line.pop(i, None)
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

    additonal_args = (
        tuple(Name(*xs) for xs in found_names.additional_args())
        + tuple(Varname(*xs) for xs in found_varnames.additional_args())
        + tuple(Cellvar(*xs) for xs in found_cellvars.additional_args())
        + tuple(Constant(*xs) for xs in found_constants.additional_args())
    )
    return (
        tuple(tuple(instruction for instruction in block) for block in blocks),
        additonal_args,
    )


def blocks_to_bytes(
    blocks: Blocks,
    additional_args: AdditionalArgs,
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

    names = FromArgs[str]()
    varnames = FromArgs[str]()
    cellvars = FromArgs[str]()
    constants = FromArgs[ConstantValue]()

    # If we have a function, set the initial varnames to be the args
    if isinstance(block_type, FunctionBlock):
        for i, k in enumerate(block_type.args.parameters.keys()):
            varnames[i] = k

    # If it is a function block, we start with the docstring
    if isinstance(block_type, FunctionBlock) and block_type.docstring is not None:
        constants[0] = block_type.docstring

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
                        freevars,
                        names,
                        varnames,
                        cellvars,
                        constants,
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

    # Process all additional arg to record their values
    for arg in additional_args:
        from_arg(arg, block_type, freevars, names, varnames, cellvars, constants)

    # Now that we know the total number of cellvars, incremement all the freevar
    # indices by the number of cellvars, for each arg
    for block_index, block in enumerate(blocks):
        for instruction_index, instruction in enumerate(block):
            arg = instruction.arg
            if isinstance(arg, Freevar):
                args[block_index, instruction_index] += len(cellvars)

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
        names.to_tuple(),
        varnames.to_tuple(),
        cellvars.to_tuple(),
        constants.to_tuple(),
    )


def to_arg(
    opcode: int,
    arg: int,
    next_offset: int,
    found_names: ToArgs[str],
    found_varnames: ToArgs[str],
    freevars: tuple[str, ...],
    found_cellvars: ToArgs[str],
    found_constants: ToArgs[ConstantValue],
) -> Arg:
    if opcode in dis.hasjabs:
        return Jump((2 if _ATLEAST_310 else 1) * arg, False)
    elif opcode in dis.hasjrel:
        return Jump(next_offset + ((2 if _ATLEAST_310 else 1) * arg), True)
    elif opcode in dis.hasname:
        return Name(*found_names.found_index(arg))
    elif opcode in dis.haslocal:
        return Varname(*found_varnames.found_index(arg))
    elif opcode in dis.hasfree:
        # The cell vars are indexed first then the freevars.
        is_cellvar = arg < len(found_cellvars)
        if is_cellvar:
            return Cellvar(*found_cellvars.found_index(arg))
        # Index into freevars with remaining arg
        return Freevar(freevars[arg - len(found_cellvars)])
    elif opcode in dis.hasconst:
        return Constant(*found_constants.found_index(arg))
    elif opcode < HAVE_ARGUMENT:
        return NoArg(arg)
    return arg


def from_arg(
    arg: Arg,
    block_type: BlockType,
    freevars: tuple[str, ...],
    names: FromArgs[str],
    varnames: FromArgs[str],
    cellvars: FromArgs[str],
    constants: FromArgs[ConstantValue],
) -> int:
    if isinstance(arg, NoArg):
        return arg._arg
    # Use 1 as the arg_value, which will be update later
    if isinstance(arg, Jump):
        return 1
    if isinstance(arg, Name):
        return names.add(arg.name, arg._index_override)
    if isinstance(arg, Varname):
        return varnames.add(arg.varname, arg._index_override)
    if isinstance(arg, Freevar):
        return freevars.index(arg.freevar)
    if isinstance(arg, Cellvar):
        return cellvars.add(arg.cellvar, arg._index_override)
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
        arg_is_string = isinstance(arg.constant, str)
        no_override = arg._index_override is None
        if docstring_is_none and first_const and arg_is_string and no_override:
            constants[0] = None

        return constants.add(arg.constant, arg._index_override)
    return arg


T = TypeVar("T")


@dataclass
class ToArgs(Generic[T]):
    _args: tuple[T, ...]
    # Mapping of the actual index argument to the position it was
    # found
    _index_to_order: dict[int, int] = field(default_factory=dict)

    def found_index(self, index: int) -> tuple[T, Optional[int]]:
        if index not in self._index_to_order:
            self._index_to_order[index] = len(self._args)
        wrong_position = self._index_to_order[index] != index
        return self._args[index], index if wrong_position else None

    def __len__(self) -> int:
        return len(self._args)

    def additional_args(self) -> Iterable[tuple[T, Optional[int]]]:
        for i in range(len(self._args)):
            if i not in self._index_to_order:
                yield self.found_index(i)


@dataclass
class FromArgs(Generic[T]):
    _i_to_arg: dict[int, T] = field(default_factory=dict)
    _arg_to_i: dict[T, int] = field(default_factory=dict)

    def __setitem__(self, i: int, arg: T) -> None:
        if i in self._i_to_arg:
            assert self._i_to_arg[i] == arg
        self._i_to_arg[i] = arg
        self._arg_to_i[arg] = i

    def __len__(self) -> int:
        return len(self._i_to_arg)

    def __bool__(self) -> bool:
        return bool(self._i_to_arg)

    def to_tuple(self) -> Tuple[T, ...]:
        return tuple(v for _, v, in sorted(self._i_to_arg.items()))

    def add(self, arg: T, index_override: Optional[int]) -> int:
        """
        Add an argument, returning it's final index
        """
        if index_override is not None:
            self[index_override] = arg
            return index_override
        if arg in self._arg_to_i:
            return self._arg_to_i[arg]
        index = len(self)
        self[index] = arg
        return index


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
