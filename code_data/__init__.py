"""
Transform Python code objects into data, and vice versa.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from types import CodeType
from typing import Tuple

from .blocks import Blocks, blocks_to_bytes, bytes_to_blocks, verify_block
from .dataclass_hide_default import DataclassHideDefault
from .flags_data import FlagsData, from_flags_data, to_flags_data
from .line_mapping import LineMapping, from_line_mapping, to_line_mapping

__all__ = ["CodeData", "to_code_data", "from_code_data"]
__version__ = "0.0.0"


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
    # retrieve the blocks and pop off used line mapping
    blocks = bytes_to_blocks(code.co_code, line_mapping)
    return CodeData(
        blocks,
        line_mapping,
        code.co_argcount,
        posonlyargcount,
        code.co_kwonlyargcount,
        code.co_nlocals,
        code.co_stacksize,
        to_flags_data(code.co_flags),
        tuple(map(to_code_constant, code.co_consts)),
        code.co_names,
        code.co_varnames,
        code.co_filename,
        code.co_name,
        code.co_firstlineno,
        code.co_freevars,
        code.co_cellvars,
    )


def from_code_data(code_data: CodeData) -> CodeType:
    """
    Serialize python data structures into a CodeType.

    :rtype: types.CodeType
    """
    consts = tuple(map(from_code_constant, code_data.consts))
    flags = from_flags_data(code_data.flags)
    code, line_mapping = blocks_to_bytes(code_data.blocks)
    line_mapping.update(code_data.additional_line_mapping)
    line_table = from_line_mapping(line_mapping)

    # https://github.com/python/cpython/blob/cd74e66a8c420be675fd2fbf3fe708ac02ee9f21/Lib/test/test_code.py#L217-L232
    # Only include posonlyargcount on 3.8+
    if sys.version_info >= (3, 8):
        return CodeType(
            code_data.argcount,
            code_data.posonlyargcount,
            code_data.kwonlyargcount,
            code_data.nlocals,
            code_data.stacksize,
            flags,
            code,
            consts,
            code_data.names,
            code_data.varnames,
            code_data.filename,
            code_data.name,
            code_data.firstlineno,
            line_table,
            code_data.freevars,
            code_data.cellvars,
        )
    else:
        return CodeType(
            code_data.argcount,
            code_data.kwonlyargcount,
            code_data.nlocals,
            code_data.stacksize,
            flags,
            code,
            consts,
            code_data.names,
            code_data.varnames,
            code_data.filename,
            code_data.name,
            code_data.firstlineno,
            line_table,
            code_data.freevars,
            code_data.cellvars,
        )


@dataclass
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

    # A list of additional line offsets for bytecode instructions
    # past the range which exist, which were eliminated by the compiler.
    additional_line_mapping: LineMapping = field(default_factory=LineMapping)

    # number of arguments (not including keyword only arguments, * or ** args)
    argcount: int = field(default=0)

    # number of positional only arguments
    posonlyargcount: int = field(default=0)

    # number of keyword only arguments (not including ** arg)
    kwonlyargcount: int = field(default=0)

    # number of local variables
    nlocals: int = field(default=0)

    # virtual machine stack space required
    stacksize: int = field(default=1)

    # code flags
    flags: FlagsData = field(default_factory=set)

    # TODO: https://github.com/metadsl/python-code-data/issues/35 Make consts and names inline
    # tuple of constants used in the bytecode
    # All code objects are recursively transformed to CodeData objects
    consts: Tuple[object, ...] = field(default=(None,))

    # tuple of names of local variables
    names: Tuple[str, ...] = field(default=tuple())

    # tuple of names of arguments and local variables
    varnames: Tuple[str, ...] = field(default=tuple())

    # name of file in which this code object was created
    filename: str = field(default="<string>")

    # name with which this code object was defined
    name: str = field(default="<module>")

    # TODO: Remove and infer from line table
    # number of first line in Python source code
    firstlineno: int = field(default=1)

    # tuple of names of free variables (referenced via a function’s closure)
    freevars: Tuple[str, ...] = field(default=tuple())
    # tuple of names of cell variables (referenced by containing scopes)
    cellvars: Tuple[str, ...] = field(default=tuple())

    def _verify(self) -> None:
        verify_block(self.blocks)


def to_code_constant(value: object) -> object:
    if isinstance(value, CodeType):
        return to_code_data(value)
    return value


def from_code_constant(value: object) -> object:
    if isinstance(value, CodeData):
        return from_code_data(value)
    return value
