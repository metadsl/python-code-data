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
                _additional_constants=tuple(),
                _additional_names=tuple(),
                _additional_varnames=tuple(),
                _additional_line=None,
                _first_line_number_override=None,
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
            replace(x, _index_override=None, value=normalize(x.value)),
        )
    if isinstance(x, (Name, Varname, Cellvar)):
        return cast(T, replace(x, _index_override=None))
    if isinstance(x, tuple):
        return cast(T, tuple(map(normalize, x)))
    return x
