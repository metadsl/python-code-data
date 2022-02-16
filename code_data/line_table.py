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


def to_mapping(code: CodeType) -> LineMapping:
    expanded_items = bytes_to_items(code.co_lnotab)
    collapsed_items = collapse_items(expanded_items)
    max_offset = len(code.co_code)
    return items_to_mapping(collapsed_items, max_offset)


def from_mapping(offset_to_line: LineMapping) -> bytes:

    # return items_to_bytes(offset_to_line)
    return items_to_bytes(expand_items(mapping_to_items(offset_to_line)))


@dataclass
class LineTableItem:
    line_offset: int
    bytecode_offset: int


Items = list[LineTableItem]
ExpandedItems = NewType("ExpandedItems", Items)
CollapsedItems = NewType("CollapsedItems", Items)


@dataclass
class LineMapping:
    # Mapping of bytecode offset to the line number associated with it
    offset_to_line: dict[int, int]
    # Mapping of bytecode offset to list of additional line offsets emited after
    # They should always sum to 0, and are a no-op, but are sometimes emitted anyways,
    # so we want to preserve them for isomporphism.
    offset_to_noop_line_offsets: dict[int, list[int]]


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
        if (
            item.bytecode_offset == 0
            and collapsed_items
            and (item.line_offset > 127 or item.line_offset <= -128)
        ):
            collapsed_items[-1].line_offset += item.line_offset
        # If there is no line offset, then we add the bytecode offset to the next
        # item
        elif item.line_offset == 0 and item.bytecode_offset != 0:
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
        emitted_extra = False

        # While the bytecode offset is to large, emit the 0, 255 item
        while bytecode_offset > 255:
            expanded_items.append(LineTableItem(line_offset=0, bytecode_offset=255))
            bytecode_offset -= 255
            emitted_extra = True
        # While the line offset is too large, emit the max line offset and remainting bytecode offset
        while line_offset > 127:
            expanded_items.append(
                LineTableItem(line_offset=127, bytecode_offset=bytecode_offset)
            )
            line_offset -= 127
            bytecode_offset = 0
            emitted_extra = True

        # Same if its too small
        while line_offset <= -128:
            expanded_items.append(
                LineTableItem(line_offset=-128, bytecode_offset=bytecode_offset)
            )
            line_offset += 128
            bytecode_offset = 0
            emitted_extra = True
        # If we have extra we haven't emited, add a last one.
        # Also emit a last one, even if we don't and we had a negative jump
        # (for some reason this always emits an extra jump)
        if line_offset != 0 or bytecode_offset != 0 or not emitted_extra:
            expanded_items.append(
                LineTableItem(line_offset=line_offset, bytecode_offset=bytecode_offset)
            )
    return expanded_items


def items_to_mapping(items: CollapsedItems, max_offset: int) -> LineMapping:
    offset_to_line: dict[int, int] = {}
    offset_to_noop_line_offsets: dict[int, list[int]] = {}
    current_item_offset = 0
    last_bytecode_offset = 0
    current_line = 1
    # Iterate through each bytecode offset and find the line number for it
    for bytecode_offset in range(0, max_offset, 2):
        # if we haven't exhausted all the line table items
        if current_item_offset < len(items):
            # and the current bytecode offset difference is equal to the next line table
            # item difference, then advance the line table item.
            current_item = items[current_item_offset]
            if (bytecode_offset - last_bytecode_offset) == current_item.bytecode_offset:
                current_line += current_item.line_offset
                current_item_offset += 1
                last_bytecode_offset = bytecode_offset
            # special case for if the bytecode offset difference of this item is 0 and
            # this is not the first item.
            # If this is the case, then these as noop line changes, which should end up back at the same line
            while (
                current_item_offset < len(items)
                and items[current_item_offset].bytecode_offset == 0
            ):
                # append or create default
                noop_offsets = offset_to_noop_line_offsets.get(bytecode_offset, [])
                offset_to_noop_line_offsets[bytecode_offset] = noop_offsets

                noop_offsets.append(items[current_item_offset].line_offset)
                current_item_offset += 1
        # Otherwise save as the current line
        offset_to_line[bytecode_offset] = current_line
    return LineMapping(
        offset_to_line=offset_to_line,
        offset_to_noop_line_offsets=offset_to_noop_line_offsets,
    )


def mapping_to_items(mapping: LineMapping) -> CollapsedItems:
    items = cast(CollapsedItems, [])
    last_line_number = 1
    last_bytecode_offset = 0
    for bytecode_offset, line_number in mapping.offset_to_line.items():
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
        # Emit a list of noop line offset, if they were encoded, after the original offset.
        no_op_line_offsets = mapping.offset_to_noop_line_offsets.get(
            bytecode_offset, []
        )
        # assert sum(no_op_line_offsets) == 0
        for line_offset in no_op_line_offsets:
            items.append(LineTableItem(line_offset=line_offset, bytecode_offset=0))

    return items


LineTable = Union[bytes, LineMapping]
