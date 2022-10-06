from __future__ import annotations

from math import isnan
from types import CodeType
from typing import Union

from . import CodeData, ConstantValue, InnerConstant

__all__ = ["to_constant", "from_constant", "InnerConstant"]


def to_constant(value: Union[InnerConstant, CodeType]) -> ConstantValue:
    if isinstance(value, CodeType):
        return CodeData.from_code(value)
    return value


def from_constant(value: ConstantValue) -> object:
    if isinstance(value, CodeData):
        return value.to_code()
    return value


def constant_key(value: ConstantValue) -> object:
    """
    Similar to Python's `_PyCode_ConstantKey` except nan values area all replaced with
    a global
    """
    if isinstance(value, CodeData):
        return value
    return inner_constant_key(value)


def inner_constant_key(value: ConstantValue) -> object:
    """
    Similar to Python's `_PyCode_ConstantKey` except nan values area all replaced with
    a global
    """
    if isinstance(value, (str, type(None), bytes, type(...))):
        return value
    if isinstance(value, (bool, int)):
        return (type(value), value)
    if isinstance(value, float):
        return (type(value), replace_nan(value), is_neg_zero(value))
    if isinstance(value, complex):
        return (
            type(value),
            replace_nan(value.real),
            replace_nan(value.imag),
            is_neg_zero(value.real),
            is_neg_zero(value.imag),
        )
    if isinstance(value, tuple):
        return tuple(map(constant_key, value))
    if isinstance(value, frozenset):
        return frozenset(map(constant_key, value))
    raise NotImplementedError(f"Unsupported constant type: {type(value)}")


def is_neg_zero(value: float) -> bool:
    return str(value) == "-0.0"


def replace_nan(value: float) -> Union[float, str]:
    """
    Replace nan with a constant so that nan == nan
    """
    if isnan(value):
        return "nan"
    return value
