from __future__ import annotations

import marshal
import pathlib
import pkgutil
import warnings
from importlib.abc import Loader
from types import CodeType
from typing import Iterable


def module_codes() -> Iterable[tuple[str, str, CodeType]]:
    """
    In order to test the code_data, we try to get a sample of bytecode,
    by walking all our packages and trying to load every module.
    Note that although this doesn't require the code to be executable,
    `walk_packages` does require it, so this will ignore any modules
    """
    # which raise errors on import.

    with warnings.catch_warnings():
        # Ignore warning on find_module which will be deprecated in Python 3.12
        # Worry about it later!
        warnings.simplefilter("ignore")
        for mi in pkgutil.walk_packages(onerror=lambda _name: None):
            loader: Loader = mi.module_finder.find_module(mi.name)  # type: ignore
            try:
                code = loader.get_code(mi.name)  # type: ignore
            except SyntaxError:
                continue
            if code:
                source = loader.get_source(mi.name)  # type: ignore
                yield mi.name, source, code


CACHE_FILE = pathlib.Path(".module_cache")


def modules_codes_cached() -> list[tuple[str, str, CodeType]]:
    """
    Cached version of `module_codes`, cached on disk file.
    """
    if CACHE_FILE.exists():
        with CACHE_FILE.open("rb") as f:
            return marshal.load(f)
    else:
        codes = list(module_codes())
        with CACHE_FILE.open("wb") as f:
            marshal.dump(codes, f)
        return codes


def all_module_codes_cached() -> list[CodeType]:
    """
    Retrn all the module codes recursively.
    """
    all_code_objects: list[CodeType] = []

    def process(code: CodeType) -> None:
        all_code_objects.append(code)
        for const in code.co_consts:
            if isinstance(const, CodeType):
                process(const)

    for name, _, code in modules_codes_cached():
        process(code)
    return all_code_objects
