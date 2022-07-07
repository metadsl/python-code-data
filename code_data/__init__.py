"""
Transform Python code objects into data, and vice versa.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from types import CodeType
from typing import FrozenSet, Optional, Tuple, Union

# Only introduced in Python 3.10
# https://github.com/python/cpython/pull/22336
if sys.version_info >= (3, 10):
    from types import EllipsisType

from .blocks import (
    Blocks,
    blocks_to_bytes,
    bytes_to_blocks,
    normalize_blocks,
    verify_block,
)
from .dataclass_hide_default import DataclassHideDefault
from .flags_data import FlagsData, from_flags_data, to_flags_data
from .line_mapping import LineMapping, from_line_mapping, to_line_mapping

__all__ = ["CodeData", "to_code_data", "from_code_data"]
__version__ = "0.0.0"


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
    _additional_line_mapping: LineMapping = field(
        default_factory=LineMapping
    )

    # The first line number to use for the bytecode, if it doesn't match
    # the first line number in the line table.
    _first_line_number_override: Optional[int] = field(default=None)

    # Additional names to include, which do not appear in any instructions,
    # Mapping of index in the names list to the name
    _additional_names: dict[int, str] = field(default_factory=dict)

    # Additional constants to include, which do not appear in any instructions,
    # Mapping of index in the names list to the name
    _additional_constants: dict[int, ConstantDataType] = field(
        default_factory=dict
    )

    # The type of block this is
    type: BlockType = field(default=None)

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

    # tuple of names of arguments and local variables
    varnames: Tuple[str, ...] = field(default=tuple())

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

    def normalize(self) -> None:
        """
        Removes all fields from the bytecode that do not effect its semantics, but only
        its serialization. This includes things like the order of the `co_consts` array,
        the number of extended args for some bytecodes, etc.
        """
        self._additional_constants = {}
        self._additional_names = {}
        self._additional_line_mapping = LineMapping()
        self._first_line_number_override = None
        normalize_blocks(self.blocks)


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
    first_line_number_override = line_mapping.set_first_line(code.co_firstlineno)

    constants = tuple(map(to_code_constant, code.co_consts))

    flag_data = to_flags_data(code.co_flags)

    fn_flags = flag_data & FN_FLAGS
    if len(fn_flags) == 0:
        block_type = None
    elif len(fn_flags) == 2:
        # Use the first const as a docstring if its a string
        # https://github.com/python/cpython/blob/da8be157f4e275c4c32b9199f1466ed7e52f62cf/Objects/funcobject.c#L33-L38
        # TODO: Maybe just assume that first arg is not docstring if it's none? Naw...
        docstring_in_consts = False
        docstring: Optional[str] = None
        if constants:
            first_constant = constants[0]
            if isinstance(first_constant, str) or first_constant is None:
                docstring_in_consts = True
                docstring = first_constant
        block_type = FunctionBlock(docstring, docstring_in_consts)
        flag_data -= FN_FLAGS
    else:
        raise ValueError(f"Expected both flags to represent function: {fn_flags}")

    # retrieve the blocks and pop off used line mapping
    blocks, additional_names, additional_constants = bytes_to_blocks(
        code.co_code, line_mapping, code.co_names, constants, block_type
    )
    return CodeData(
        blocks,
        line_mapping,
        first_line_number_override,
        additional_names,
        additional_constants,
        block_type,
        code.co_argcount,
        posonlyargcount,
        code.co_kwonlyargcount,
        code.co_nlocals,
        code.co_stacksize,
        flag_data,
        code.co_varnames,
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
        flags_data = FN_FLAGS | flags_data
    flags = from_flags_data(flags_data)
    code, line_mapping, names, constants = blocks_to_bytes(
        code_data.blocks,
        code_data._additional_names,
        code_data._additional_constants,
        code_data.type,
    )

    consts = tuple(map(from_code_constant, constants))

    line_mapping.update(code_data._additional_line_mapping)
    first_line_no = line_mapping.trim_first_line(code_data._first_line_number_override)

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
            names,
            code_data.varnames,
            code_data.filename,
            code_data.name,
            first_line_no,
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
            names,
            code_data.varnames,
            code_data.filename,
            code_data.name,
            first_line_no,
            line_table,
            code_data.freevars,
            code_data.cellvars,
        )


# The type of block this is, as we can infer from the flags.
# https://github.com/python/cpython/blob/5506d603021518eaaa89e7037905f7a698c5e95c/Include/symtable.h#L13
BlockType = Union["FunctionBlock", None]


@dataclass
class FunctionBlock(DataclassHideDefault):
    docstring: Optional[str] = field(default=None)
    # Set to false if the docstring is not saved as a constant. In this case, it
    # must be 0. This happens for list comprehensions
    docstring_in_consts: bool = field(default=True)


ConstantDataType = Union[
    "ConstantInt",
    str,
    "ConstantFloat",
    None,
    "ConstantBool",
    bytes,
    "EllipsisType",
    CodeData,
    "ConstantComplex",
    "ConstantSet",
    "ConstantTuple",
]


def to_code_constant(value: object) -> ConstantDataType:
    if isinstance(value, CodeType):
        return to_code_data(value)
    if isinstance(value, (str, type(None), bytes, type(...))):
        return value
    if isinstance(value, bool):
        return ConstantBool(value)
    if isinstance(value, int):
        return ConstantInt(value)
    if isinstance(value, float):
        return ConstantFloat(value, is_neg_zero(value))
    if isinstance(value, complex):
        return ConstantComplex(value, is_neg_zero(value.real), is_neg_zero(value.imag))
    if isinstance(value, tuple):
        return ConstantTuple(tuple(map(to_code_constant, value)))
    if isinstance(value, frozenset):
        return ConstantSet(frozenset(map(to_code_constant, value)))
    raise NotImplementedError(f"Unsupported constant type: {type(value)}")


def from_code_constant(value: ConstantDataType) -> object:
    if isinstance(value, CodeData):
        return from_code_data(value)
    if isinstance(value, ConstantTuple):
        return tuple(map(from_code_constant, value.value))
    if isinstance(value, ConstantSet):
        return frozenset(map(from_code_constant, value.value))
    if isinstance(value, (ConstantBool, ConstantInt, ConstantFloat, ConstantComplex)):
        return value.value
    return value


# Wrap these in types, so that, say, bytecode with constants of 1
# are not equal to bytecodes of constants of True.


@dataclass(frozen=True)
class ConstantBool(DataclassHideDefault):
    value: bool = field(metadata={"positional": True})


@dataclass(frozen=True)
class ConstantInt(DataclassHideDefault):
    value: int = field(metadata={"positional": True})


@dataclass(frozen=True)
class ConstantFloat(DataclassHideDefault):
    value: float = field(metadata={"positional": True})
    # Store if the value is negative 0, so that == distinguishes between 0.0 and -0.0
    is_neg_zero: bool = field(default=False)


@dataclass(frozen=True)
class ConstantComplex(DataclassHideDefault):
    value: complex = field(metadata={"positional": True})
    # Store if the value is negative 0, so that == distinguishes between 0.0 and -0.0
    real_is_neg_zero: bool = field(default=False)
    imag_is_neg_zero: bool = field(default=False)


# We need to wrap the data structures in dataclasses to be able to represent
# them with MyPy, since it doesn't support recursive types
# https://github.com/python/mypy/issues/731
@dataclass(frozen=True)
class ConstantTuple(DataclassHideDefault):
    # Make not positional until rich supports positional tuples
    # https://github.com/Textualize/rich/pull/2379
    value: tuple[ConstantDataType, ...] = field(metadata={"positional": False})


@dataclass(frozen=True)
class ConstantSet(DataclassHideDefault):
    value: FrozenSet[ConstantDataType] = field(metadata={"positional": True})


def is_neg_zero(value: float) -> bool:
    return str(value) == "-0.0"
