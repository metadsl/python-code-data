from __future__ import annotations

from types import CodeType

from . import (
    ConstantBool,
    ConstantComplex,
    ConstantEllipsis,
    ConstantFloat,
    ConstantInt,
    ConstantSet,
    ConstantTuple,
    ConstantValue,
    InnerConstant,
)

__all__ = ["to_constant", "from_constant", "InnerConstant"]


def to_constant(value: object) -> ConstantValue:
    from .code_data import CodeData

    if isinstance(value, CodeType):
        return CodeData.from_code(value)
    return to_inner_constant(value)


def from_constant(value: ConstantValue) -> object:
    from . import CodeData

    if isinstance(value, CodeData):
        return value.to_code()
    return from_inner_constant(value)


def to_inner_constant(value: object) -> InnerConstant:
    if isinstance(value, (str, type(None), bytes)):
        return value
    if isinstance(value, type(...)):
        return ConstantEllipsis()
    if isinstance(value, bool):
        return ConstantBool(value)
    if isinstance(value, int):
        return ConstantInt(value)
    if isinstance(value, float):
        return ConstantFloat(value, is_neg_zero(value))
    if isinstance(value, complex):
        return ConstantComplex(value, is_neg_zero(value.real), is_neg_zero(value.imag))
    if isinstance(value, tuple):
        return ConstantTuple(tuple(map(to_inner_constant, value)))
    if isinstance(value, frozenset):
        return ConstantSet(frozenset(map(to_inner_constant, value)))
    raise NotImplementedError(f"Unsupported constant type: {type(value)}")


def from_inner_constant(value: InnerConstant) -> object:
    if isinstance(value, ConstantTuple):
        return tuple(map(from_inner_constant, value.value))
    if isinstance(value, ConstantSet):
        return frozenset(map(from_inner_constant, value.value))
    if isinstance(value, (ConstantBool, ConstantInt, ConstantFloat, ConstantComplex)):
        return value.value
    if isinstance(value, ConstantEllipsis):
        return ...
    return value


def is_neg_zero(value: float) -> bool:
    return str(value) == "-0.0"
