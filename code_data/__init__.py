"""
Transform Python code objects into data, and vice versa.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from inspect import _ParameterKind
from types import CodeType
from typing import FrozenSet, Iterator, Optional, Tuple, Union

from typing_extensions import Literal

from .dataclass_hide_default import DataclassHideDefault

__version__ = "1.0.1"


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
    type: TypeOfCode = field(default=None)

    # tuple of names of free variables (referenced via a function’s closure)
    freevars: tuple[str, ...] = field(default=())

    # Whether the annotations future flag is active
    future_annotations: bool = field(default=False)

    # Whether the CO_NESTED flag is set. This is not used anymore and has no impact
    # https://github.com/python/cpython/pull/19660
    _nested: bool = field(default=False)
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
    arg: Arg = field(metadata={"positional": True}, default_factory=lambda: NoArg())

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

    constant: ConstantValue = field(metadata={"positional": True})  # type: ignore
    # Optional override for the position if it is not ordered by occurance in the code.
    _index_override: Optional[int] = field(default=None)

    def __eq__(self, __o: object) -> bool:
        from ._constants import constant_key

        if not isinstance(__o, Constant):
            return False
        if self._index_override != __o._index_override:
            return False
        return constant_key(self.constant) == constant_key(__o.constant)


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


@dataclass(frozen=True)
class NoArg(DataclassHideDefault):
    """
    Represents an argument for an opcode with an arg.

    It stores the value override, to recreate it byte-for-byte, but this value is
    unused.
    """

    _arg: int = field(default=0)


Arg = Union[int, Jump, Name, Varname, Constant, Freevar, Cellvar, NoArg]


# TODO: Add:
# 6. Comparison lookup
# 7. format value
# 8. Generator kind
# 9. A function lookup

AdditionalArg = Union[Name, Varname, Cellvar, Constant]
AdditionalArgs = Tuple[AdditionalArg, ...]


InnerConstant = Union[
    FrozenSet["InnerConstant"],
    Tuple["InnerConstant", ...],
    str,
    None,
    bytes,
    bool,
    float,
    int,
    # Exclude ellipsis type because it breaks sphinx
    # EllipsisType,
    complex,
]

# The CodeData can only be a top level constant, not nested in any data structures
ConstantValue = Union[InnerConstant, CodeData]


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
class Function(DataclassHideDefault):
    """
    A block of code in a function.
    """

    args: Args = field(default_factory=Args, metadata={"positional": True})
    docstring: Optional[str] = field(default=None)
    type: FunctionType = field(default=None)


# The type of code this is, as we can infer from the flags.
# https://github.com/python/cpython/blob/5506d603021518eaaa89e7037905f7a698c5e95c/Include/symtable.h#L13
TypeOfCode = Union[Function, None]


FunctionType = Optional[Literal["GENERATOR", "COROUTINE", "ASYNC_GENERATOR"]]


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
    "Function": {
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
            "type": {
                "type": "string",
                "enum": ["GENERATOR", "COROUTINE", "ASYNC_GENERATOR"],
            },
        },
        "description": Function.__doc__,
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
            "type": {"$ref": "#/definitions/Function"},
            "freevars": {"type": "array", "items": {"type": "string"}, "default": []},
            "_nested": {"type": "boolean", "default": False},
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
    "NoArg": {
        "type": "object",
        "required": [],
        "properties": {
            "_arg": {"type": "integer", "default": 0},
        },
        "description": NoArg.__doc__,
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
            {"type": "boolean"},
            {"type": "null"},
            {"$ref": "#/definitions/ConstantString"},
            {"$ref": "#/definitions/ConstantNumber"},
            {"$ref": "#/definitions/ConstantEllipsis"},
            {"$ref": "#/definitions/ConstantComplex"},
            {"$ref": "#/definitions/ConstantFrozenset"},
            {"$ref": "#/definitions/ConstantTuple"},
            {"$ref": "#/definitions/ConstantBytes"},
            {"$ref": "#/definitions/CodeData"},
        ]
    },
    "ConstantString": {
        "anyOf": [
            {"type": "string"},
            {
                "type": "object",
                "required": ["string"],
                "properties": {"string": {"type": "string"}},
                "description": (
                    "A string with surrogat epairs which "
                    "cannot be encoded to unicode"
                ),
            },
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
        "description": "a complex number",
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
        "description": "a frozen set",
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
        "required": ["name"],
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
                    {"$ref": "#/definitions/NoArg"},
                    {"type": "integer"},
                ],
                "default": {"_arg": 0},
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
