"""
Transform Python code objects into data, and vice versa.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from inspect import _ParameterKind
from math import isnan
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

    # name of file in which this code object was created
    filename: str

    # the first line number of the code object
    first_line_number: int

    # name with which this code object was defined
    name: str

    # virtual machine stack space required
    stacksize: int

    # The type of block this is
    type: BlockType = field(default=None)

    # tuple of names of free variables (referenced via a function’s closure)
    freevars: tuple[str, ...] = field(default=())

    # code flags
    flags: FlagsData = field(default_factory=frozenset)

    # On Python < 3.10 sometimes there is a line mapping for an additional line
    # for the bytecode after the last one in the code, for an instruction which was
    # compiled away. Include this so we can represent the line mapping faithfully.
    _additional_line: Optional[AdditionalLine] = field(default=None)

    # Additional args which are not part of the bytecode, but were included in it.
    _additional_args: AdditionalArgs = field(default=())

    @classmethod
    def from_code(cls, code: CodeType) -> CodeData:
        """
        Parse a CodeType into python data structure.

        :type code: types.CodeType
        """
        from ._code_data import to_code_data

        return to_code_data(code)

    def to_code(self) -> CodeType:
        """
        Convert the code data type back to code.

        :rtype: types.CodeType
        """
        from ._code_data import from_code_data

        return from_code_data(self)

    @classmethod
    def from_json_data(cls, json_data: dict) -> CodeData:
        """
        Parse a JSON data structure into a CodeData.

        The JSON structure must be of the schema `code_data.JSON_SCHEMA`
        """
        from ._json_data import code_data_from_json

        return code_data_from_json(json_data)

    def to_json_data(self) -> dict:
        """
        Convert the code data to a JSON data structure.

        The schema of the returned json is available at `code_data.JSON_SCHEMA`
        """
        from ._json_data import code_data_to_json

        return code_data_to_json(self)

    def normalize(self) -> CodeData:
        """

        Removes all fields from the bytecode that do not effect its semantics, but only
        its serialization.

        This includes things like the order of the `co_consts` array, the number of
        extended args for some bytecodes, etc.
        """
        from ._normalize import normalize

        return normalize(self)

    def __iter__(self) -> Iterator[CodeData]:
        """
        Iterates through all the code data which are included,
        by processing the arguments recursively.
        """
        for block in self.blocks:
            for instruction in block:
                arg = instruction.arg
                if isinstance(arg, Constant) and isinstance(arg.constant, CodeData):
                    yield arg.constant

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


Arg = Union[int, "Jump", "Name", "Varname", "Constant", "Freevar", "Cellvar"]


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

    constant: ConstantValue = field(metadata={"positional": True})
    # Optional override for the position if it is not ordered by occurance in the code.
    _index_override: Optional[int] = field(default=None)


@dataclass(frozen=True)
class Freevar(DataclassHideDefault):
    """
    A freevar argument.
    """

    freevar: str = field(metadata={"positional": True})


@dataclass(frozen=True)
class Cellvar(DataclassHideDefault):
    """
    A cellvar argument.
    """

    cellvar: str = field(metadata={"positional": True})
    _index_override: Optional[int] = field(default=None)


# TODO: Add:
# 5. An unused value
# 6. Comparison lookup
# 7. format value
# 8. Generator kind
# 9. A function lookup

AdditionalArg = Union[Name, Varname, Cellvar, Constant]
AdditionalArgs = Tuple[AdditionalArg, ...]


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
    str,
    None,
    bytes,
    "ConstantBool",
    "ConstantFloat",
    "ConstantInt",
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

    def __eq__(self, __o: object) -> bool:
        """
        Override equality to mark nans as equal
        """
        if not isinstance(__o, ConstantFloat):
            return False
        if isnan(self.value) and isnan(__o.value):
            return True
        return (self.value, self.is_neg_zero) == (__o.value, __o.is_neg_zero)


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
    # TODO: Rename to frozenset
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
        from ._args import args_to_parameters

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


# Initially generate by https://github.com/s-knibbs/dataclasses-jsonschema
# and then modified to fit our needs.
_definitions = {
    "FunctionBlock": {
        "type": "object",
        "properties": {
            "args": {
                "$ref": "#/definitions/Args",
                "default": {
                    "positional_only": [],
                    "positional_or_keyword": [],
                    "var_positional": None,
                    "keyword_only": [],
                    "var_keyword": None,
                },
            },
            "docstring": {"type": "string"},
        },
        "description": FunctionBlock.__doc__,
    },
    "Args": {
        "type": "object",
        "properties": {
            "positional_only": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
            },
            "positional_or_keyword": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
            },
            "var_positional": {"type": "string"},
            "keyword_only": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
            },
            "var_keyword": {"type": "string"},
        },
        "description": Args.__doc__,
    },
    "AdditionalLine": {
        "type": "object",
        "properties": {
            "line": {"type": "integer"},
            "additional_offsets": {
                "type": "array",
                "items": {"type": "integer"},
                "default": [],
            },
        },
        "description": AdditionalLine.__doc__,
    },
    "CodeData": {
        "type": "object",
        "required": ["blocks", "filename", "first_line_number", "name", "stacksize"],
        "properties": {
            "blocks": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Instruction"},
                },
            },
            "filename": {"type": "string"},
            "first_line_number": {"type": "integer"},
            "name": {"type": "string"},
            "stacksize": {"type": "integer"},
            "type": {"$ref": "#/definitions/FunctionBlock"},
            "freevars": {"type": "array", "items": {"type": "string"}, "default": []},
            "flags": {"type": "array", "items": {"type": "string"}, "default": []},
            "_additional_line": {"$ref": "#/definitions/AdditionalLine"},
            "_additional_args": {
                "type": "array",
                "items": {
                    "anyOf": [
                        {"$ref": "#/definitions/Name"},
                        {"$ref": "#/definitions/Varname"},
                        {"$ref": "#/definitions/Cellvar"},
                        {"$ref": "#/definitions/Constant"},
                    ]
                },
                "default": [],
            },
        },
        "description": CodeData.__doc__,
    },
    "Jump": {
        "type": "object",
        "required": ["target"],
        "properties": {
            "target": {"type": "integer"},
            "relative": {"type": "boolean", "default": False},
        },
        "description": Jump.__doc__,
    },
    "Name": {
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "_index_override": {"type": "integer"},
        },
        "description": Name.__doc__,
    },
    "Varname": {
        "type": "object",
        "required": ["varname"],
        "properties": {
            "varname": {"type": "string"},
            "_index_override": {"type": "integer"},
        },
        "description": Varname.__doc__,
    },
    "Constant": {
        "type": "object",
        "properties": {
            "constant": {"$ref": "#/definitions/ConstantValue"},
            "_index_override": {"type": "integer"},
        },
        "description": Constant.__doc__,
    },
    "ConstantValue": {
        "anyOf": [
            {"type": "string"},
            {"type": "boolean"},
            {"type": "null"},
            {"$ref": "#/definitions/ConstantNumber"},
            {"$ref": "#/definitions/ConstantEllipsis"},
            {"$ref": "#/definitions/ConstantComplex"},
            {"$ref": "#/definitions/ConstantFrozenset"},
            {"$ref": "#/definitions/ConstantTuple"},
            {"$ref": "#/definitions/ConstantBytes"},
            {"$ref": "#/definitions/CodeData"},
        ]
    },
    "ConstantEllipsis": {
        "type": "object",
        "required": ["type"],
        "properties": {
            "type": {"type": "string", "enum": ["ellipsis"]},
        },
        "description": "An ellipsis constant",
    },
    "ConstantNumber": {
        "anyOf": [
            {
                "type": "object",
                "required": ["float"],
                "properties": {
                    "float": {"type": "string", "enum": ["nan", "inf", "-inf"]},
                },
                "description": "A special float constant",
            },
            {
                "type": "object",
                "required": ["int"],
                "properties": {
                    "int": {"type": "string"},
                },
                "description": "A string encocding of an integer",
            },
            {"type": "number"},
        ]
    },
    "ConstantComplex": {
        "type": "object",
        "required": ["real", "imag"],
        "properties": {
            "real": {"$ref": "#/definitions/ConstantNumber"},
            "imag": {"$ref": "#/definitions/ConstantNumber"},
        },
        "description": ConstantComplex.__doc__,
    },
    "ConstantBytes": {
        "type": "object",
        "required": ["bytes"],
        "properties": {
            "bytes": {"type": "string"},
        },
        "description": "Base 64 encoded bytes",
    },
    "ConstantFrozenset": {
        "type": "object",
        "required": ["frozenset"],
        "properties": {
            "frozenset": {
                "type": "array",
                "items": {"$ref": "#/definitions/ConstantValue"},
            }
        },
        "description": ConstantSet.__doc__,
    },
    "ConstantTuple": {
        "type": "array",
        "items": {"$ref": "#/definitions/ConstantValue"},
    },
    "Freevar": {
        "type": "object",
        "required": ["freevar"],
        "properties": {"freevar": {"type": "string"}},
        "description": Freevar.__doc__,
    },
    "Cellvar": {
        "type": "object",
        "required": ["cellvar"],
        "properties": {
            "cellvar": {"type": "string"},
            "_index_override": {"type": "integer"},
        },
        "description": Cellvar.__doc__,
    },
    "Instruction": {
        "type": "object",
        "required": ["name", "arg"],
        "properties": {
            "name": {"type": "string"},
            "arg": {
                "anyOf": [
                    {"$ref": "#/definitions/Jump"},
                    {"$ref": "#/definitions/Name"},
                    {"$ref": "#/definitions/Varname"},
                    {"$ref": "#/definitions/Constant"},
                    {"$ref": "#/definitions/Freevar"},
                    {"$ref": "#/definitions/Cellvar"},
                    {"type": "integer"},
                ]
            },
            "_n_args_override": {"type": "integer"},
            "line_number": {"type": "integer"},
            "_line_offsets_override": {
                "type": "array",
                "items": {"type": "integer"},
                "default": [],
            },
        },
        "description": Instruction.__doc__,
    },
}

# The JSON schema for the Python code object
JSON_SCHEMA = {
    "title": "Python Code Object",
    "definitions": _definitions,
    "$ref": "#/definitions/CodeData",
}
