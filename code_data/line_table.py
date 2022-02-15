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
    print(expanded_items)
    # return expanded_items
    collapsed_items = collapse_items(expanded_items)
    max_offset = len(code.co_code)
    return items_to_mapping(collapsed_items, max_offset)


def from_mapping(offset_to_line: OffsetToLine) -> bytes:
    # return items_to_bytes(offset_to_line)
    return items_to_bytes(expand_items(mapping_to_items(offset_to_line)))


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
            LineTableItem(
                bytecode_offset=b[i],
                # Convert byte for line offset into integer based on it being a signed integer
                line_offset=int.from_bytes([b[i + 1]], "big", signed=True),
            )
            for i in range(0, len(b), 2)
        ],
    )


def items_to_bytes(items: ExpandedItems) -> bytes:
    return bytes(
        chain.from_iterable(
            (
                [
                    item.bytecode_offset,
                    # convert possibly negative int to signed integer
                    item.line_offset & 255,
                ]
                for item in items
            )
        )
    )


def collapse_items(items: ExpandedItems) -> CollapsedItems:
    collapsed_items = cast(CollapsedItems, [])

    additional_bytecode_offset = 0
    for item in items:
        # If there is no bytecode offset, then we assume our line offset
        # was too large to store in one byte, so we add our current line offset to our previous
        # (unless it is the first item, then the bytecode offset will always be 0)
        if item.bytecode_offset == 0 and collapsed_items:
            collapsed_items[-1].line_offset += item.line_offset
        # If there is no line offset, then we add the bytecode offset to the next
        # item
        elif item.line_offset == 0:
            additional_bytecode_offset += item.bytecode_offset
        else:
            collapsed_items.append(
                LineTableItem(
                    line_offset=item.line_offset,
                    bytecode_offset=item.bytecode_offset + additional_bytecode_offset,
                )
            )
            additional_bytecode_offset = 0
    return collapsed_items


def expand_items(items: CollapsedItems) -> ExpandedItems:
    expanded_items = cast(ExpandedItems, [])
    for item in items:
        line_offset = item.line_offset
        bytecode_offset = item.bytecode_offset
        # While the bytecode offset is to large, emit the 0, 255 item
        while bytecode_offset > 255:
            expanded_items.append(LineTableItem(line_offset=0, bytecode_offset=255))
            bytecode_offset -= 255
        # While the line offset is too large, emit the max line offset and remainting bytecode offset
        while line_offset > 127:
            expanded_items.append(
                LineTableItem(line_offset=127, bytecode_offset=bytecode_offset)
            )
            line_offset -= 127
            bytecode_offset = 0
        # If either of them having remaing, emit those
        if line_offset > 0 or bytecode_offset > 0:
            expanded_items.append(
                LineTableItem(line_offset=line_offset, bytecode_offset=bytecode_offset)
            )
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
