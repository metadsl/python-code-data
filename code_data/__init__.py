"""
Transform Python code objects into data, and vice versa.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace
from types import CodeType
from typing import Optional, Tuple, Union

from code_data.args import Args, ArgsInput

from .blocks import (
    AdditionalConstants,
    AdditionalNames,
    AdditionalVarnames,
    Blocks,
    blocks_to_bytes,
    bytes_to_blocks,
    verify_block,
)
from .constants import from_code_constant, to_code_constant
from .dataclass_hide_default import DataclassHideDefault
from .flags_data import FlagsData, from_flags_data, to_flags_data
from .line_mapping import AdditionalLine, from_line_mapping, to_line_mapping
from .normalize import normalize

__all__ = ["CodeData", "to_code_data", "from_code_data"]
__version__ = "0.0.0"


@dataclass(frozen=True)
class CodeData(DataclassHideDefault):
    """
    A code object is what is seralized on disk as PYC file. It is the lowest
    abstraction level CPython provides before execution.

    This class is meant to a be a data description of a code object,
    where the types of the attributes can help us understand what the different
    possible options are.

    All recursive code object are translated to code data as well.

    From https://docs.python.org/3/library/inspect.html
    """

    # Bytecode instructions
    blocks: Blocks = field(metadata={"positional": True})

    # On Python < 3.10 sometimes there is a line mapping for an additional line
    # for the bytecode after the last one in the code, for an instruction which was
    # compiled away. Include this so we can represent the line mapping faithfully.
    _additional_line: Optional[AdditionalLine] = field(default=None)

    # The first line number to use for the bytecode, if it doesn't match
    # the first line number in the line table.
    _first_line_number_override: Optional[int] = field(default=None)

    # Additional names to include, which do not appear in any instructions,
    # Mapping of index in the names list to the name
    _additional_names: AdditionalNames = field(default=tuple())

    # Additional varnames to include, which do not appear in any instructions.
    # This does not include args, which are always included!
    _additional_varnames: AdditionalVarnames = field(default=tuple())

    # Additional constants to include, which do not appear in any instructions,
    # Mapping of index in the names list to the name
    _additional_constants: AdditionalConstants = field(default=tuple())

    # The type of block this is
    type: BlockType = field(default=None)

    # number of local variables
    nlocals: int = field(default=0)

    # virtual machine stack space required
    stacksize: int = field(default=1)

    # code flags
    flags: FlagsData = field(default_factory=frozenset)

    # name of file in which this code object was created
    filename: str = field(default="<string>")

    # name with which this code object was defined
    name: str = field(default="<module>")

    # tuple of names of free variables (referenced via a function’s closure)
    freevars: Tuple[str, ...] = field(default=tuple())
    # tuple of names of cell variables (referenced by containing scopes)
    cellvars: Tuple[str, ...] = field(default=tuple())

    def _verify(self) -> None:
        verify_block(self.blocks)
        # Verify hashable
        hash(self)


@normalize.register
def _normalize_code_data(code_data: CodeData) -> CodeData:
    return replace(
        code_data,
        blocks=normalize(code_data.blocks),
        _additional_constants=tuple(),
        _additional_names=tuple(),
        _additional_varnames=tuple(),
        _additional_line=None,
        _first_line_number_override=None,
    )


# Functions should have both of these flags set
# https://github.com/python/cpython/blob/443370d8acd107da235d2e9758e06ab3583be4ea/Python/compile.c#L5348
FN_FLAGS = {"NEWLOCALS", "OPTIMIZED"}


def to_code_data(code: CodeType) -> CodeData:
    """
    Parse a CodeType into python data structure.

    :type code: types.CodeType
    """
    if sys.version_info >= (3, 8):
        posonlyargcount = code.co_posonlyargcount
    else:
        posonlyargcount = 0

    line_mapping = to_line_mapping(code)

    # TODO: #54 For functions, do 1 + this line
    first_line_number_override = line_mapping.set_first_line(code.co_firstlineno)

    constants = tuple(map(to_code_constant, code.co_consts))

    flags_data = to_flags_data(code.co_flags)

    args, flags_data = Args.from_input(
        ArgsInput(
            argcount=code.co_argcount,
            posonlyargcount=posonlyargcount,
            kwonlyargcount=code.co_kwonlyargcount,
            varnames=code.co_varnames,
            flags_data=flags_data,
        )
    )

    # TODO: Make this special type constructor?
    fn_flags = flags_data & FN_FLAGS
    if len(fn_flags) == 0:
        block_type = None
        assert not args.names(), "if this isn't a function, it shouldn't have args"
    elif len(fn_flags) == 2:
        # Use the first const as a docstring if its a string
        # https://github.com/python/cpython/blob/da8be157f4e275c4c32b9199f1466ed7e52f62cf/Objects/funcobject.c#L33-L38
        docstring = (
            constants[0] if constants and isinstance(constants[0], str) else None
        )
        block_type = FunctionBlock(args, docstring)
        flags_data -= FN_FLAGS
    else:
        raise ValueError(f"Expected both flags to represent function: {fn_flags}")

    # retrieve the blocks and pop off used line mapping
    (
        blocks,
        additional_names,
        additional_varnames,
        additional_constants,
    ) = bytes_to_blocks(
        code.co_code,
        line_mapping,
        code.co_names,
        code.co_varnames,
        constants,
        block_type,
        args,
    )
    next_line = line_mapping.pop_additional_line(len(code.co_code))
    return CodeData(
        blocks,
        next_line,
        first_line_number_override,
        additional_names,
        additional_varnames,
        additional_constants,
        block_type,
        code.co_nlocals,
        code.co_stacksize,
        flags_data,
        code.co_filename,
        code.co_name,
        code.co_freevars,
        code.co_cellvars,
    )


def from_code_data(code_data: CodeData) -> CodeType:
    """
    Serialize python data structures into a CodeType.

    :rtype: types.CodeType
    """
    flags_data = code_data.flags
    if isinstance(code_data.type, FunctionBlock):
        flags_data = flags_data | FN_FLAGS
    code, line_mapping, names, varnames, constants = blocks_to_bytes(
        code_data.blocks,
        code_data._additional_names,
        code_data._additional_varnames,
        code_data._additional_constants,
        code_data.type,
    )

    consts = tuple(map(from_code_constant, constants))

    if code_data._additional_line:
        line_mapping.add_additional_line(code_data._additional_line, len(code))

    if isinstance(code_data.type, FunctionBlock):
        args_input = code_data.type.args.to_input(flags_data)
        argcount = args_input.argcount
        posonlyargcount = args_input.posonlyargcount
        kwonlyargcount = args_input.kwonlyargcount
        flags_data = args_input.flags_data

        assert (
            varnames[: len(args_input.varnames)] == args_input.varnames
        ), "varnames should start with args"
    else:
        argcount = 0
        posonlyargcount = 0
        kwonlyargcount = 0

    flags = from_flags_data(flags_data)

    first_line_no = line_mapping.trim_first_line(code_data._first_line_number_override)

    line_table = from_line_mapping(line_mapping)
    # https://github.com/python/cpython/blob/cd74e66a8c420be675fd2fbf3fe708ac02ee9f21/Lib/test/test_code.py#L217-L232
    # Only include posonlyargcount on 3.8+
    if sys.version_info >= (3, 8):
        return CodeType(
            argcount,
            posonlyargcount,
            kwonlyargcount,
            code_data.nlocals,
            code_data.stacksize,
            flags,
            code,
            consts,
            names,
            varnames,
            code_data.filename,
            code_data.name,
            first_line_no,
            line_table,
            code_data.freevars,
            code_data.cellvars,
        )
    else:
        if posonlyargcount:
            raise NotImplementedError(
                "Positional only args are only supported on Python 3.8+"
            )
        return CodeType(
            argcount,
            kwonlyargcount,
            code_data.nlocals,
            code_data.stacksize,
            flags,
            code,
            consts,
            names,
            varnames,
            code_data.filename,
            code_data.name,
            first_line_no,
            line_table,
            code_data.freevars,
            code_data.cellvars,
        )


# The type of block this is, as we can infer from the flags.
# https://github.com/python/cpython/blob/5506d603021518eaaa89e7037905f7a698c5e95c/Include/symtable.h#L13
# TODO: Rename, overlaps with "blocks"
BlockType = Union["FunctionBlock", None]


@dataclass(frozen=True)
class FunctionBlock(DataclassHideDefault):
    args: Args = field(default_factory=Args, metadata={"positional": True})
    docstring: Optional[str] = field(default=None)
