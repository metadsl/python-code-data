import pkgutil
import warnings
from importlib.abc import Loader
from types import CodeType
from typing import Iterable

__all__ = ["module_codes"]


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
