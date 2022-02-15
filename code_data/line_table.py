from __future__ import annotations

import sys
from dataclasses import dataclass
from itertools import chain
from types import CodeType
from typing import NewType, Union, cast

__all__ = ["LineTable", "to_line_table", "from_line_table"]


def to_line_table(code: CodeType) -> LineTable:
    if sys.version_info >= (3, 10):
        return code.co_linetable  # type: ignore
    return to_mapping(code)


def from_line_table(line_table: LineTable) -> bytes:
    if isinstance(line_table, bytes):
        return line_table
    return from_mapping(line_table)


def to_mapping(code: CodeType) -> OffsetToLine:
    expanded_items = bytes_to_items(code.co_lnotab)
    collapsed_items = collapse_items(expanded_items)
    max_offset = len(code.co_code)
    return items_to_mapping(collapsed_items, max_offset)


def from_mapping(offset_to_line: OffsetToLine) -> bytes:
    return items_to_bytes(expand_items((mapping_to_items(offset_to_line))))


@dataclass
class LineTableItem:
    line_offset: int
    bytecode_offset: int


Items = list[LineTableItem]
ExpandedItems = NewType("ExpandedItems", Items)
CollapsedItems = NewType("CollapsedItems", Items)
OffsetToLine = dict[int, int]


def bytes_to_items(b: bytes) -> ExpandedItems:
    return cast(
        ExpandedItems,
        [
            LineTableItem(bytecode_offset=b[i], line_offset=b[i + 1])
            for i in range(0, len(b), 2)
        ],
    )


def items_to_bytes(items: ExpandedItems) -> bytes:
    return bytes(
        chain.from_iterable(
            ([item.bytecode_offset, item.line_offset] for item in items)
        )
    )


def collapse_items(items: ExpandedItems) -> CollapsedItems:
    collapsed_items = cast(CollapsedItems, [])
    for item in items:
        if item.bytecode_offset == 0 and collapsed_items:
            collapsed_items[-1].line_offset += item.line_offset
        else:
            collapsed_items.append(
                LineTableItem(item.line_offset, item.bytecode_offset)
            )
    return collapsed_items


def expand_items(items: CollapsedItems) -> ExpandedItems:
    expanded_items = cast(ExpandedItems, [])
    for item in items:
        line_offset = item.line_offset
        bytecode_offset = item.bytecode_offset
        while line_offset:
            written_line_offset = min(line_offset, 127)
            written_bytecode_offset = bytecode_offset
            expanded_items.append(
                LineTableItem(
                    line_offset=written_line_offset,
                    bytecode_offset=written_bytecode_offset,
                )
            )
            line_offset -= written_line_offset
            bytecode_offset -= written_bytecode_offset
    return expanded_items


def items_to_mapping(items: CollapsedItems, max_offset: int) -> OffsetToLine:
    mapping: OffsetToLine = {}
    current_item_offset = 0
    last_bytecode_offset = 0
    current_line = 1
    # Iterate through each bytecode offset and find the line number for it
    for bytecode_offset in range(0, max_offset, 2):
        # If the bytecode offset is the same as the next offset
        if current_item_offset < len(items):
            current_item = items[current_item_offset]
            if (bytecode_offset - last_bytecode_offset) == current_item.bytecode_offset:
                current_line += current_item.line_offset
                current_item_offset += 1
                last_bytecode_offset = bytecode_offset
        mapping[bytecode_offset] = current_line
    return mapping


def mapping_to_items(mapping: OffsetToLine) -> CollapsedItems:
    items = cast(CollapsedItems, [])
    last_line_number = 1
    last_bytecode_offset = 0
    for bytecode_offset, line_number in mapping.items():
        # If the line changes, emit an item
        if line_number != last_line_number:
            items.append(
                LineTableItem(
                    line_offset=line_number - last_line_number,
                    bytecode_offset=bytecode_offset - last_bytecode_offset,
                )
            )
            last_line_number = line_number
            last_bytecode_offset = bytecode_offset
    return items


LineTable = Union[bytes, OffsetToLine]
