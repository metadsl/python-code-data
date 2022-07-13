from __future__ import annotations

from dataclasses import dataclass, field
from types import CodeType
from typing import TYPE_CHECKING, FrozenSet, Union

from .dataclass_hide_default import DataclassHideDefault

if TYPE_CHECKING:
    # Only available 3.9+
    from types import EllipsisType

    # Circular reference
    from . import CodeData

ConstantDataType = Union[
    "ConstantInt",
    str,
    "ConstantFloat",
    None,
    "ConstantBool",
    bytes,
    "EllipsisType",
    "CodeData",
    "ConstantComplex",
    "ConstantSet",
    "ConstantTuple",
]


def to_code_constant(value: object) -> ConstantDataType:
    from . import to_code_data

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
    from . import CodeData, from_code_data

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
    value: tuple[ConstantDataType, ...] = field(metadata={"positional": True})


@dataclass(frozen=True)
class ConstantSet(DataclassHideDefault):
    value: FrozenSet[ConstantDataType] = field(metadata={"positional": True})


def is_neg_zero(value: float) -> bool:
    return str(value) == "-0.0"
