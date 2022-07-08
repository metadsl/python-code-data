import functools
import typing


# Should make it identity, but currently error with mypy
# https://github.com/python/mypy/issues/13040
@functools.singledispatch
def normalize(x: typing.Any) -> typing.Any:
    """
    Removes all fields from the bytecode that do not effect its semantics, but only
    its serialization.

    This includes things like the order of the `co_consts` array, the number of
    extended args for some bytecodes, etc.
    """
    return x
