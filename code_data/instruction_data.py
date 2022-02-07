"""
Represent Python Bytecode instructions as a data structure.

"""


from __future__ import annotations

import dis
import sys
from dataclasses import dataclass, field
from itertools import chain
from typing import Iterable, Optional

from .dataclass_hide_default import DataclassHideDefault


def instructions_from_bytes(b: bytes) -> Iterable[InstructionData]:
    args = []
    for i in range(0, len(b), 2):
        opcode = b[i]
        args.append(b[i + 1])
        # Build up our list of args whenever we have an extended arg
        if opcode == dis.EXTENDED_ARG:
            continue
        yield InstructionData.from_bytes(offset=i, args=args, opcode=opcode)
        args = []


# Bytecode instructions jumps refer to the instruction offset, instead of byte
# offset in Python >= 3.10 due to this PR https://github.com/python/cpython/pull/25069
ATLEAST_310 = sys.version_info >= (3, 10)


@dataclass
class InstructionData(DataclassHideDefault):
    # The bytes offset of the instruction
    offset: int

    # The name of the instruction
    name: str

    # The integer value of the arg
    arg: int

    # The number of args, if it differs form the instrsize
    # Note: in Python >= 3.10 we can calculute this from the instruction size,
    # using `instrsize`, but in python < 3.10, sometimes instructions are prefixed
    # with extended args with value 0 (not sure why or how), so we need to save
    # the value manually to recreate the instructions
    n_args_override: Optional[int] = field(repr=False, default=1)

    # The bytes offset of the jump target, if it does jump.
    jump_target_offset: Optional[int] = field(default=None)

    @classmethod
    def from_bytes(cls, offset: int, opcode: int, args: list[int]) -> InstructionData:

        name = dis.opname[opcode]

        # Compute arg by starting with highest byte and working down
        arg, *rest_args = args
        for next_arg in rest_args:
            arg = (arg << 8) | next_arg

        # Copied from dis.findlabels
        jump_target_offset = (
            (2 if ATLEAST_310 else 1) * arg
            if opcode in dis.hasjabs
            else offset + 2 + ((2 if ATLEAST_310 else 1) * arg)
            if opcode in dis.hasjrel
            else None
        )

        min_n_args = instrsize(arg)
        n_args = len(args)
        # The number of args should be at least the minimum
        assert n_args >= min_n_args
        # Store the number of args if this is a jump instruction
        # This is needed to preserve isomporphic behavior. Otherwise
        # there are cases where jump instructions could be different values
        # (and have different number of args), but point to the same instruction
        # offset.
        n_args_override = n_args if jump_target_offset is not None else None

        return cls(
            offset=offset,
            name=name,
            arg=arg,
            jump_target_offset=jump_target_offset,
            n_args_override=n_args_override,
        )

    def bytes(self) -> Iterable[int]:
        # Duplicate semantics of write_op_arg
        # to produce the the right number of extended arguments
        # https://github.com/python/cpython/blob/b2e5794870eb4728ddfaafc0f79a40299576434f/Python/wordcode_helpers.h#L22-L44
        for i in reversed(range(self.n_args())):
            yield self.opcode() if i == 0 else dis.EXTENDED_ARG
            yield (self.arg >> (8 * i)) & 0xFF

    def n_args(self) -> int:
        if self.n_args_override is not None:
            return self.n_args_override
        return instrsize(self.arg)

    def opcode(self) -> int:
        return dis.opmap[self.name]

    def offsets(self) -> Iterable[int]:
        """
        Returns all the offsets for the instruction, including those for the extended
        args that appear before it
        """
        for i in range(self.n_args()):
            yield self.offset - (i * 2)


def instrsize(arg: int) -> int:
    """
    Minimum number of code units necessary to encode instruction with
    EXTENDED_ARGs

    From https://github.com/python/cpython/blob/b2e5794870eb4728ddfaafc0f79a40299576434f/Python/wordcode_helpers.h#L11-L20
    """
    return 1 if arg <= 0xFF else 2 if arg <= 0xFFFF else 3 if arg <= 0xFFFFFF else 4
