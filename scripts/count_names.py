# flake8: noqa
"""
Count how many names are not looked at.

7/12/2022
"""

from __future__ import annotations

import collections
import dis
import logging
from dis import pretty_flags
from types import CodeType

from rich.logging import RichHandler

from code_data.module_codes import modules_codes_cached

FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger(__name__)

log.info("Loading codes")
codes = modules_codes_cached()
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


def names(code):
    all_possible = set(range(len(code.co_varnames)))
    used: set[int] = set()
    for offset, op, arg in dis._unpack_opargs(code.co_code):  # type: ignore
        if op in dis.haslocal:
            used.add(arg)
    all_possible = set(range(len(code.co_varnames)))
    # Verify only using in range
    assert used.issubset(all_possible)
    return used, all_possible


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


def use_all_names(code: CodeType) -> bool:
    """
    Whether the code objects uses
    """
    used, all_possible = names(code)
    return used == all_possible


def used_all_local_names(code: CodeType) -> bool:
    """
    Whether the code objects uses all the name
    """
    used, all_possible = names(code)
    arg_name_indices = set(range(total_args(code)))
    return (used - arg_name_indices) == (all_possible - arg_name_indices)


log.info(
    "Used all local names? %r",
    collections.Counter(map(used_all_local_names, all_code_objects)),
)
has_unused_names = filter(lambda c: not used_all_local_names(c), all_code_objects)
code = next(has_unused_names)
# used, possible = names(first_unused_name)
# log.info("First unused name: %r", {"used ": used, "unused": possible - used})


def fn():
    if False:
        a = 100
        z = a


print(used_all_local_names(fn.__code__))
