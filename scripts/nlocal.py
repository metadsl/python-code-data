# flake8: noqa
"""
Are the nlocals equal to the rest of the co_varnames after the args?
A: No, they are just equal to the total varnames!
7/13/2022
"""

from __future__ import annotations

import collections
import logging
from dis import pretty_flags
from types import CodeType

from rich.logging import RichHandler

from code_data.module_codes import module_codes, modules_codes_cached

FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger(__name__)

log.info("Loading codes")
codes = list(module_codes())
log.info("found %r modules", len(codes))
all_code_objects: list[CodeType] = []


def process(code: CodeType) -> None:
    all_code_objects.append(code)
    for const in code.co_consts:
        if isinstance(const, CodeType):
            process(const)


for name, _, code in codes:
    process(code)
log.info("found %r code objects", len(all_code_objects))


def total_args(code: CodeType) -> int:
    flags_string = pretty_flags(code.co_flags)

    x = code.co_argcount + code.co_kwonlyargcount
    if "VARARGS" in flags_string:
        x += 1
    if "VARKEYWORDS" in flags_string:
        x += 1
    return x


assert total_args((lambda x, y, *z, **a: None).__code__) == 4
assert total_args((lambda x, y, **a: None).__code__) == 3
assert total_args((lambda x, y, *, b=None, **a: None).__code__) == 4


def nlocals_after_varnames(code: CodeType) -> bool:
    """
    Whether the nlocals is equal to all the varnames after the args
    """
    nlocals = code.co_nlocals
    varnames = len(code.co_varnames)
    return nlocals == varnames


log.info(
    "nlocals after varnames? %r",
    collections.Counter(map(nlocals_after_varnames, all_code_objects)),
)
