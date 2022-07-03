"""
Decodes the linear list of instructions into a sequence of blocks.
Every instruction that is jumped to starts a new block.
"""

from __future__ import annotations

import ctypes
import dis
import sys
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple, Union

from code_data.line_mapping import LineMapping

from .dataclass_hide_default import DataclassHideDefault


def bytes_to_blocks(b: bytes, line_mapping: LineMapping) -> Blocks:
    """
    Parse a sequence of bytes as a sequence of blocks of instructions.
    """
    # First, iterate through bytes to make instructions while also making set of all the
    # targets
    # List of bytecode offsets and instructions
    offsets_and_instruction: list[tuple[int, Instruction]] = []
    # Set of all instruction offsets which are targets of jump blocks
    # The targets always includes the first block
    targets_set = {0}

    for opcode, arg, n_args, offset, next_offset in _parse_bytes(b):

        # Compute the jump targets, initially with just the byte offset
        # Once we know all the block targets, we will transform to be block offsets
        processed_arg = to_arg(opcode, arg, next_offset)
        if isinstance(processed_arg, Jump):
            targets_set.add(processed_arg.target)
            # Store the number of args if this is a jump instruction
            # This is needed to preserve isomporphic behavior. Otherwise
            # there are cases where jump instructions could be different values
            # (and have different number of args), but point to the same instruction
            # offset.
            n_args_override = n_args
        else:
            processed_arg = arg

        instruction = Instruction(
            name=dis.opname[opcode],
            arg=processed_arg,
            n_args_override=n_args_override,
            line_number=line_mapping.offset_to_line.pop(offset),
            line_offsets_override=line_mapping.offset_to_additional_line_offsets.pop(
                offset, []
            ),
        )
        offsets_and_instruction.append((offset, instruction))

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
            instruction.arg.target = targets.index(instruction.arg.target)
        block.append(instruction)

    return {i: block for i, block in enumerate(blocks)}


def blocks_to_bytes(blocks: Blocks) -> Tuple[bytes, LineMapping]:
    # First compute mapping from block to offset
    changed_instruction_lengths = True
    # So that we know the bytecode offsets for jumps when iterating though instructions
    block_index_to_instruction_offset: dict[int, int] = {}

    # Mapping of block index, instruction index, to integer arg values
    args: dict[tuple[int, int], int] = {}

    # Iterate through all blocks and change jump instructions to offsets
    while changed_instruction_lengths:

        current_instruction_offset = 0
        # First go through and update all the instruction blocks
        for block_index, block in blocks.items():
            block_index_to_instruction_offset[block_index] = current_instruction_offset
            for instruction_index, instruction in enumerate(block):
                if (block_index, instruction_index) in args:
                    arg_value = args[block_index, instruction_index]
                else:
                    arg_value = from_arg(instruction.arg)
                    args[block_index, instruction_index] = arg_value
                n_instructions = instruction.n_args_override or _instrsize(arg_value)
                current_instruction_offset += n_instructions
        # Then go and update all the jump instructions. If any of them
        # change the number of instructions needed for the arg, repeat
        changed_instruction_lengths = False
        current_instruction_offset = 0
        for block_index, block in blocks.items():
            for instruction_index, instruction in enumerate(block):
                arg = instruction.arg
                arg_value = args[block_index, instruction_index]
                n_instructions = instruction.n_args_override or _instrsize(arg_value)
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
                        not instruction.n_args_override
                        and n_instructions != _instrsize(new_arg_value)
                    ):
                        changed_instruction_lengths = True
                    args[block_index, instruction_index] = new_arg_value

    # Finally go assemble the bytes and the line mapping
    bytes_: list[int] = []
    line_mapping = LineMapping()
    for block_index, block in blocks.items():
        for instruction_index, instruction in enumerate(block):
            offset = len(bytes_)

            line_mapping.offset_to_line[offset] = instruction.line_number
            if instruction.line_offsets_override:
                line_mapping.offset_to_additional_line_offsets[
                    offset
                ] = instruction.line_offsets_override

            arg_value = args[block_index, instruction_index]
            n_args = instruction.n_args_override or _instrsize(arg_value)
            # Duplicate semantics of write_op_arg
            # to produce the the right number of extended arguments
            # https://github.com/python/cpython/blob/b2e5794870eb4728ddfaafc0f79a40299576434f/Python/wordcode_helpers.h#L22-L44
            for i in reversed(range(n_args)):
                bytes_.append(
                    dis.opmap[instruction.name] if i == 0 else dis.EXTENDED_ARG
                )
                bytes_.append((arg_value >> (8 * i)) & 0xFF)

    return bytes(bytes_), line_mapping


def to_arg(opcode: int, arg: int, next_offset: int) -> Arg:
    if opcode in dis.hasjabs:
        return Jump((2 if _ATLEAST_310 else 1) * arg, False)
    elif opcode in dis.hasjrel:
        return Jump(next_offset + ((2 if _ATLEAST_310 else 1) * arg), True)
    return arg


def from_arg(arg: Arg) -> int:
    # Use 1 as the arg_value, which will be update later
    if isinstance(arg, Jump):
        return 1
    return arg


def verify_block(blocks: Blocks) -> None:
    """
    Verify that the blocks are valid, by making sure every
    instruction that jumps can find it's block.
    """
    for block in blocks.values():
        assert block, "Block is empty"
        for instruction in block:
            arg = instruction.arg
            if isinstance(arg, Jump):
                assert arg.target in range(len(blocks)), "Jump target is out of range"


@dataclass
class Instruction(DataclassHideDefault):
    # The name of the instruction
    name: str = field(metadata={"positional": True})

    # The integer value of the arg
    arg: Arg = field(metadata={"positional": True})

    # The number of args, if it differs form the instrsize
    # Note: in Python >= 3.10 we can calculute this from the instruction size,
    # using `instrsize`, but in python < 3.10, sometimes instructions are prefixed
    # with extended args with value 0 (not sure why or how), so we need to save
    # the value manually to recreate the instructions
    n_args_override: Optional[int] = field(repr=False)

    # The line number of the instruction
    line_number: Optional[int] = field(default=None)

    # A number of additional line offsets to include in the line mapping
    # Unneccessary to preserve line semantics, but needed to preserve isomoprhic
    # byte-for-byte mapping
    # Only need in Python < 3.10
    line_offsets_override: list[int] = field(default_factory=list)


@dataclass
class Jump(DataclassHideDefault):
    # The block index of the target
    target: int = field(metadata={"positional": True})
    # Whether the jump is absolute or relative
    relative: bool = field(repr=False)


@dataclass
class Name(DataclassHideDefault):
    """
    A name argument.
    """

    name: str = field(metadata={"positional": True})


# TODO: Add:
# 1. constant lookup
# 2. a name lookup
# 3. a local lookup
# 5. An unused value
# 6. Comparison lookup
# 7. format value
# 8. Generator kind

Arg = Union[int, Jump]


# dict mapping block offset to list of instructions in the block
Blocks = Dict[int, List[Instruction]]

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
    return 1 if arg <= 0xFF else 2 if arg <= 0xFFFF else 3 if arg <= 0xFFFFFF else 4


# The number of bits in a signed int
_c_int_bit_size = ctypes.sizeof(ctypes.c_int()) * 8
# The maximum value that can be stored in a signed int
_c_int_upper_limit = (2 ** (_c_int_bit_size - 1)) - 1
# The number of values that can be stored in a signed int
_c_int_length = 2**_c_int_bit_size
