from __future__ import annotations

import ctypes
import dis
import sys
from dis import _get_instructions_bytes  # type: ignore
from types import CodeType
from typing import Any, Iterable, Optional, cast

import fastjsonschema
import orjson

from . import JSON_SCHEMA, CodeData
from ._blocks import verify_block
from ._line_mapping import (
    USE_LINETABLE,
    LineMapping,
    bytes_to_items,
    collapse_items,
    expand_items,
    items_to_bytes,
    items_to_mapping,
    mapping_to_items,
)


def verify_code(code: CodeType, debug=True) -> None:
    """
    Verify that converting to a CodeData works on this code object.

    If debug is True, then we will print out the differences between the two.
    """
    code_data = CodeData.from_code(code)

    assert hash(code_data), "verify hashable"
    verify_block(code_data.blocks)

    resulting_code = code_data.to_code()

    # If we aren't debugging just assert they are equal
    if not debug:
        assert code == resulting_code
    # Otherwise, we want to get a more granular error message, if possible
    elif code != resulting_code:
        # Otherwise, we start analyzing the code in more granular ways to try to narrow
        # down which part of the code object is different.

        # First, we check if the primitives are the same, minus the line table
        assert code_to_primitives(code) == code_to_primitives(resulting_code)

        # If they are the same, we can check if the line table is the same
        verify_line_mapping(code, resulting_code)

        # If the line table is the same, we can verify that the constant keys are the
        # same
        verify_constant_keys(code, resulting_code)

        # If all those are the same, then we aren't sure why the code objects are
        # different and just assert they are equal
        assert code == resulting_code

        # We used to compare the marhshalled bytes as well, but this was unstable
        # due to whether the constants had refernces to them, so we disabled it

    verify_normalize(code_data)
    verify_json(code_data)


validate = fastjsonschema.compile(JSON_SCHEMA)


def verify_json(code_data: CodeData) -> None:
    """
    Verify that the JSON serialization of this code object is the same.
    """
    json_data = code_data.to_json_data()
    validate(json_data)
    resulting_json_data = orjson.loads(orjson.dumps(json_data))
    assert json_data == resulting_json_data, "JSON value changed after serialization"
    assert (
        CodeData.from_json_data(resulting_json_data) == code_data
    ), "JSON value results in different code data"


def verify_normalize(code_data: CodeData) -> None:
    """
    Verify that after normalizing, going to/from bytecode produces the same code_data.
    """
    code_data = code_data.normalize()
    normalized_code = code_data.to_code()
    new_code_data = CodeData.from_code(normalized_code)
    new_code_data = new_code_data.normalize()
    assert code_data == new_code_data


code_attributes = tuple(
    name
    for name in dir(CodeType)
    if name.startswith("co_")
    # Don't compare generated co_lines iterator returned in Python 3.10
    # When co_lntob is removed in 3.12, we need to figured out how to adapt.
    and name != "co_lines"
    # Also ignore lines
    and name != "co_lnotab" and name != "co_linetable"
)


def code_to_primitives(code: CodeType) -> dict[str, object]:
    """
    Converts a code object to primitives, for better pytest diffing.
    """
    return {
        name: (
            tuple(
                code_to_primitives(a) if isinstance(a, CodeType) else a
                for a in code.co_consts
            )
            if name == "co_consts"
            else (
                [(i.opname, i.argval) for i in _get_instructions_bytes(code.co_code)]
                if name == "co_code"
                else getattr(code, name)
            )
        )
        for name in code_attributes
    }


_PyCode_ConstantKey = ctypes.pythonapi._PyCode_ConstantKey
_PyCode_ConstantKey.restype = ctypes.py_object


def verify_constant_keys(code: CodeType, resulting_code: CodeType) -> None:
    """
    Verifies that the constant keys are the same in the code object.
    """
    for l, r in zip(code.co_consts, resulting_code.co_consts):  # noqa: E741
        if isinstance(l, CodeType):
            verify_constant_keys(l, r)
        else:
            assert _PyCode_ConstantKey(ctypes.py_object(l)) == _PyCode_ConstantKey(
                ctypes.py_object(r)
            )


def verify_line_mapping(code: CodeType, resulting_code: CodeType) -> None:
    """
    Verify the mapping type by testing each conversion layer and making sure they
    are isomorphic.

    The tests are written in this way, so we can more easily which layer is
    causing the error.
    """
    b = get_code_line_bytes(code)
    # if they are not equal, try seeing where the process failed
    if b != get_code_line_bytes(resulting_code):
        max_offset = len(code.co_code)
        expanded_items = bytes_to_items(b)
        assert items_to_bytes(expanded_items) == b, "bytes to items to bytes"

        collapsed_items = collapse_items(expanded_items, USE_LINETABLE)
        assert (
            expand_items(collapsed_items, USE_LINETABLE) == expanded_items
        ), "collapsed to expanded to collapsed"

        mapping = items_to_mapping(collapsed_items, max_offset, USE_LINETABLE)
        assert (
            mapping_to_items(mapping, USE_LINETABLE) == collapsed_items
        ), "items to mapping to items"

        assert mapping_to_line_starts(mapping, code.co_firstlineno, max_offset) == dict(
            dis.findlinestarts(code)
        ), "mapping matches dis.findlinestarts"

        if hasattr(code, "co_lines"):
            assert mapping == co_lines_to_mapping(
                cast(Any, code).co_lines(), code.co_firstlineno
            ), "mapping matches dis.co_lines"

        assert b == get_code_line_bytes(
            resulting_code
        ), "somehow line table bytes are still different"

    # Recurse on inner code objects
    for i, const in enumerate(code.co_consts):
        if isinstance(const, CodeType):
            verify_line_mapping(const, resulting_code.co_consts[i])


def get_code_line_bytes(code: CodeType) -> bytes:
    """
    Get the bytes for a line of code.
    """
    if USE_LINETABLE:
        return code.co_linetable
    return code.co_lnotab


def mapping_to_line_starts(
    mapping: LineMapping, first_line_number: int, length_code: int
) -> dict[int, int]:
    """
    Convert our mapping to a dis line starts output to verify our implementation.
    """
    line_starts_dict: dict[int, int] = {}

    last_line = None
    for bytecode, line in mapping.offset_to_line.items():
        # If we are past the end of the code, don't add anymore
        # dis does not include these, after 37
        if sys.version_info >= (3, 8) and bytecode >= length_code:
            break
        if line is not None and line != last_line:
            line_starts_dict[bytecode] = line + first_line_number
            last_line = line
    return line_starts_dict


def co_lines_to_mapping(
    co_lines: Iterable[tuple[int, int, Optional[int]]], first_line_number: int
) -> LineMapping:
    """
    Convert a code.co_lines() output to a LineMapping
    """
    offset_to_line: dict[int, Optional[int]] = {}
    for start, end, line in co_lines:
        for offset in range(start, end, 2):
            offset_to_line[offset] = None if line is None else line - first_line_number

    return LineMapping(offset_to_line)
