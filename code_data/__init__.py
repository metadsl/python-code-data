"""
Transform Python code objects into data, and vice versa.

TODO: Move all types here. Move all functions into other files. Make all things methods
for external usage.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from inspect import _ParameterKind
from types import CodeType
from typing import FrozenSet, Iterator, Optional, Tuple, Union

from .dataclass_hide_default import DataclassHideDefault

__version__ = "0.0.0"


@dataclass(frozen=True)
class CodeData(DataclassHideDefault):
    """
    The `CodeData` is a data class which contains the same information to reconstruct
    the Python CodeType, but is easier to deal with, then the bytecode pieces in there:

    A code object is what is seralized on disk as PYC file. It is the lowest
    abstraction level CPython provides before execution.

    This class is meant to a be a data description of a code object,
    where the types of the attributes can help us understand what the different
    possible options are.

    All recursive code object are translated to code data as well.

    Going back and forth to a code data object is gauranteed to be isomporphic,
    meaning all the data is preserved::

        assert CodeData.from_code(code).to_code == code

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

    @classmethod
    def from_code(cls, code: CodeType) -> CodeData:
        """
        Parse a CodeType into python data structure.

        :type code: types.CodeType
        """
        from .code_data import to_code_data

        return to_code_data(code)

    def to_code(self) -> CodeType:
        """
        Convert the code data type back to code.

        :rtype: types.CodeType
        """
        from .code_data import from_code_data

        return from_code_data(self)

    def normalize(self) -> CodeData:
        """

        Removes all fields from the bytecode that do not effect its semantics, but only
        its serialization.

        This includes things like the order of the `co_consts` array, the number of
        extended args for some bytecodes, etc.
        """
        from .normalize import normalize

        return normalize(self)

    def __iter__(self) -> Iterator[CodeData]:
        """
        Iterates through all the code data which are included,
        by processing the arguments recursively.
        """
        for block in self.blocks:
            for instruction in block:
                arg = instruction.arg
                if isinstance(arg, Constant) and isinstance(arg.value, CodeData):
                    yield arg.value

    def all_code_data(self) -> Iterator[CodeData]:
        """
        Return all the code data recursively, including itself.
        """
        yield self
        for code_data in self:
            yield from code_data.all_code_data()


FlagsData = FrozenSet[str]


# tuple of blocks, each block is a list of instructions.
Blocks = Tuple[Tuple["Instruction", ...], ...]


@dataclass(frozen=True)
class Instruction(DataclassHideDefault):
    """
    An instruction in the bytecode.
    """

    # The name of the instruction
    name: str = field(metadata={"positional": True})

    # The integer value of the arg
    arg: Arg = field(metadata={"positional": True})

    # The number of args, if it differs form the instrsize
    # Note: in Python >= 3.10 we can calculute this from the instruction size,
    # using `instrsize`, but in python < 3.10, sometimes instructions are prefixed
    # with extended args with value 0 (not sure why or how), so we need to save
    # the value manually to recreate the instructions
    _n_args_override: Optional[int] = field(default=None)

    # The line number of the instruction
    line_number: Optional[int] = field(default=None)

    # A number of additional line offsets to include in the line mapping
    # Unneccessary to preserve line semantics, but needed to preserve isomoprhic
    # byte-for-byte mapping
    # Only need in Python < 3.10
    _line_offsets_override: tuple[int, ...] = field(default=tuple())


Arg = Union[int, "Jump", "Name", "Varname", "Constant"]


@dataclass(frozen=True)
class Jump(DataclassHideDefault):
    """
    A jump argument.
    """

    # The block index of the target
    target: int = field(metadata={"positional": True})
    # Whether the jump is absolute or relative
    relative: bool = field(default=False)


@dataclass(frozen=True)
class Name(DataclassHideDefault):
    """
    A name argument.
    """

    name: str = field(metadata={"positional": True})

    # Optional override for the position of the name, if it is not ordered by occurance
    # in the code.
    _index_override: Optional[int] = field(default=None)


@dataclass(frozen=True)
class Varname(DataclassHideDefault):
    """
    A varname argument.
    """

    varname: str = field(metadata={"positional": True})

    # Optional override for the position of the name, if it is not ordered by occurance
    # in the code.
    _index_override: Optional[int] = field(default=None)


@dataclass(frozen=True)
class Constant(DataclassHideDefault):
    """
    A constant argument.
    """

    value: ConstantValue = field(metadata={"positional": True})
    # Optional override for the position if it is not ordered by occurance in the code.
    _index_override: Optional[int] = field(default=None)


# TODO: Add:
# 3. a local lookup
# 5. An unused value
# 6. Comparison lookup
# 7. format value
# 8. Generator kind


AdditionalNames = Tuple["AdditionalName", ...]
AdditionalConstants = Tuple["AdditionalConstant", ...]
AdditionalVarnames = Tuple["AdditionalVarname", ...]


@dataclass(frozen=True)
class AdditionalName(DataclassHideDefault):
    """
    An additional name argument, that was not used in the instructions
    """

    name: str = field(metadata={"positional": True})
    index: int = field(metadata={"positional": True})


@dataclass(frozen=True)
class AdditionalConstant(DataclassHideDefault):
    """
    An additional name argument, that was not used in the instructions
    """

    constant: ConstantValue = field(metadata={"positional": True})
    index: int = field(metadata={"positional": True})


@dataclass(frozen=True)
class AdditionalVarname(DataclassHideDefault):
    """
    An additional var name argument, that was not used in the instructions
    """

    varname: str = field(metadata={"positional": True})
    index: int = field(metadata={"positional": True})


# We process each constant into a `ConstantValue`, so that we can represent
# the recursive typing of the constants in a way MyPy can handle as well preserving
# the hash and equality of constants, to the standard that the code object uses. A
# code object containing a constant of `0` should not be equal to the same code object
# with a constant of `False`, even though in Python `0 == False`. So by wrapping
# the different constant types in containers with the type, this makes sure these
# are not equal:
ConstantValue = Union["InnerConstant", CodeData]

# tuples/sets can only contain these values, not the code type itself.
InnerConstant = Union[
    "ConstantInt",
    str,
    "ConstantFloat",
    None,
    "ConstantBool",
    bytes,
    "ConstantEllipsis",
    "ConstantComplex",
    "ConstantSet",
    "ConstantTuple",
]


# Wrap these in types, so that, say, bytecode with constants of 1
# are not equal to bytecodes of constants of True.


@dataclass(frozen=True)
class ConstantBool(DataclassHideDefault):
    """
    A constant bool.
    """

    value: bool = field(metadata={"positional": True})


@dataclass(frozen=True)
class ConstantInt(DataclassHideDefault):
    """
    A constant int.
    """

    value: int = field(metadata={"positional": True})


@dataclass(frozen=True)
class ConstantFloat(DataclassHideDefault):
    """
    A constant float.
    """

    value: float = field(metadata={"positional": True})
    # Store if the value is negative 0, so that == distinguishes between 0.0 and -0.0
    is_neg_zero: bool = field(default=False)


@dataclass(frozen=True)
class ConstantComplex(DataclassHideDefault):
    """
    A constant complex.
    """

    value: complex = field(metadata={"positional": True})
    # Store if the value is negative 0, so that == distinguishes between 0.0 and -0.0
    real_is_neg_zero: bool = field(default=False)
    imag_is_neg_zero: bool = field(default=False)


# We need to wrap the data structures in dataclasses to be able to represent
# them with MyPy, since it doesn't support recursive types
# https://github.com/python/mypy/issues/731
@dataclass(frozen=True)
class ConstantTuple(DataclassHideDefault):
    """
    A constant tuple.
    """

    value: tuple[InnerConstant, ...] = field(metadata={"positional": True})


@dataclass(frozen=True)
class ConstantSet(DataclassHideDefault):
    """
    A constant set.
    """

    value: FrozenSet[InnerConstant] = field(metadata={"positional": True})


@dataclass(frozen=True)
class ConstantEllipsis(DataclassHideDefault):
    """
    Use this instead of EllipsisType, because EllipsisType is not supported
    in Sphinx autodc.
    """

    def __str__(self):
        return "..."


# The type of block this is, as we can infer from the flags.
# https://github.com/python/cpython/blob/5506d603021518eaaa89e7037905f7a698c5e95c/Include/symtable.h#L13
# TODO: Rename, overlaps with "blocks"
BlockType = Union["FunctionBlock", None]


@dataclass(frozen=True)
class Args(DataclassHideDefault):
    """
    Holds the different possible args for a function
    """

    positional_only: tuple[str, ...] = field(default=())
    positional_or_keyword: tuple[str, ...] = field(default=())
    var_positional: Optional[str] = field(default=None)
    keyword_only: tuple[str, ...] = field(default=())
    var_keyword: Optional[str] = field(default=None)

    @property
    def parameters(self) -> OrderedDict[str, _ParameterKind]:
        """
        Returns the names of the args, in order, mapping to their kind.
        """
        from .args import args_to_parameters

        return args_to_parameters(self)

    def __len__(self) -> int:
        """
        Returns the number of args
        """
        return len(self.parameters)


@dataclass(frozen=True)
class FunctionBlock(DataclassHideDefault):
    """
    A block of code in a function.
    """

    args: Args = field(default_factory=Args, metadata={"positional": True})
    docstring: Optional[str] = field(default=None)


@dataclass(frozen=True)
class AdditionalLine(DataclassHideDefault):
    """
    An additional line of code, that was not used in the instructions
    """

    line: Optional[int]
    additional_offsets: tuple[int, ...] = field(default=tuple())
