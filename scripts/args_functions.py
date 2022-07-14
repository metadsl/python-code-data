"""
Check if all blocks with "args" are "functions".

7/13/2022
"""

from __future__ import annotations

import collections
import inspect
import logging
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


def is_function(code: CodeType):
    return bool(inspect.CO_OPTIMIZED & code.co_flags) and bool(
        inspect.CO_NEWLOCALS & code.co_flags
    )


def has_args(code: CodeType):
    return bool(
        code.co_argcount
        or code.co_kwonlyargcount
        or getattr(code, "co_posonlyargcount", 0)
        or (code.co_flags & inspect.CO_VARARGS)
        or (code.co_flags & inspect.CO_VARKEYWORDS)
    )


log.info(
    "Used all local names? %r",
    collections.Counter(
        (
            has_args(c),
            is_function(c),
        )
        for c in all_code_objects
    ),
)
