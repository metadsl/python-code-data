from __future__ import annotations

from dataclasses import replace
from typing import TypeVar, cast

from . import Cellvar, CodeData, Constant, Instruction, Name, Varname

T = TypeVar("T")


def normalize(x: T) -> T:

    if isinstance(x, CodeData):
        return cast(
            T,
            replace(
                x,
                blocks=normalize(x.blocks),
                _additional_args=(),
                _additional_line=None,
                _nested=False,
            ),
        )
    if isinstance(x, Instruction):
        return cast(
            T,
            replace(
                x,
                _n_args_override=None,
                _line_offsets_override=tuple(),
                arg=normalize(x.arg),
            ),
        )
    if isinstance(x, Constant):
        return cast(
            T,
            replace(x, _index_override=None, constant=normalize(x.constant)),
        )
    if isinstance(x, (Name, Varname, Cellvar)):
        return cast(T, replace(x, _index_override=None))
    if isinstance(x, tuple):
        return cast(T, tuple(map(normalize, x)))
    return x
