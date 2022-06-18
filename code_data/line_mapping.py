"""
Converts the bytecode representation of the line table into a mapping of bytecode offsets
to line offsets.

Note that the format of this field is not documented and subject to change under
every minor release. We find that it does in fact change from release to release!

Under release 3.10 it underwent a large refactor to support describing bytecode
which maps to no initial lines.
"""

from __future__ import annotations

import collections
import sys
from dataclasses import dataclass, field
from itertools import chain
from types import CodeType
from typing import List, Optional, cast

__all__ = ["LineMapping", "to_line_mapping", "from_line_mapping"]


# Whether to use the newer co_linetable field over the older co_lnotab
USE_LINETABLE = sys.version_info >= (3, 10)


def to_line_mapping(code: CodeType) -> LineMapping:
    """
    Convert a code type to a line mapping.
    """
    expanded_items = bytes_to_items(
        code.co_linetable if USE_LINETABLE else code.co_lnotab  # type: ignore
    )
    collapsed_items = collapse_items(expanded_items, USE_LINETABLE)
    max_offset = len(code.co_code)
    mapping = items_to_mapping(collapsed_items, max_offset, USE_LINETABLE)
    return mapping


def from_line_mapping(offset_to_line: LineMapping) -> bytes:
    """
    Convert a line mapping to a bytecode representation, either the co_linetable
    or co_lnotab field.
    """
    return items_to_bytes(
        expand_items(mapping_to_items(offset_to_line, USE_LINETABLE), USE_LINETABLE)
    )


@dataclass
class LineTableItem:
    line_offset: int
    bytecode_offset: int


ExpandedItems = List[LineTableItem]


@dataclass
class CollapsedLineTableItem:
    # Is only None on Python 3.10+ when using line table
    line_offset: Optional[int]
    bytecode_offset: int


CollapsedItems = List[CollapsedLineTableItem]


@dataclass
class LineMapping:
    # Mapping of bytecode offset to the line number associated with it
    offset_to_line: dict[int, Optional[int]] = field(default_factory=dict)

    # Mapping of bytecode offset to list of additional line offsets emited after
    # the first one. Only included if not the default line offset, which only
    # is split into two pieces if it's outside of the byte range to be stored in one
    offset_to_additional_line_offsets: dict[int, list[int]] = field(
        default_factory=dict
    )


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


def collapse_items(items: ExpandedItems, is_linetable: bool) -> CollapsedItems:
    """
    Collapse the bytecode and line table jumps, with any that needed
    two bytes to represent.

    from lnotab_notes.txt:

    if byte code offset jumps by more than 255 from one row to the next, or if
    source code line number jumps by more than 127 or less than -128 from one row
    to the next, more than one pair is written to the table.
    """
    collapsed_items = [
        CollapsedLineTableItem(
            line_offset=None
            if is_linetable and i.line_offset == -128
            else i.line_offset,
            bytecode_offset=i.bytecode_offset,
        )
        for i in items
    ]

    # Iterate over the items, from the end to the begining.
    # If there is a zero and the previous is at the limit,
    # then remove the current, and add it to the previous.
    for i, item, prev_item in reversed(
        [(i, collapsed_items[i], collapsed_items[i - 1]) for i in range(1, len(items))]
    ):
        # For the bytecode split, the previouse line offset should be zero
        bytecode_offset_split = (
            (item if is_linetable else prev_item).line_offset == 0
            and prev_item.bytecode_offset >= (254 if is_linetable else 255)
            and item.bytecode_offset != 0
        )
        # However, when the line offset is split, the current bytecode offset should be zero
        line_offset_split = (
            (prev_item if is_linetable else item).bytecode_offset == 0
            and (prev_item.line_offset is not None)
            and (
                prev_item.line_offset >= 127
                or prev_item.line_offset <= (-127 if is_linetable else -128)
            )
            and item.line_offset != 0
        )
        # Bytecode offset too large, so split between two
        if bytecode_offset_split or line_offset_split:
            del collapsed_items[i]
            if item.line_offset:
                prev_item.line_offset += item.line_offset  # type: ignore
            prev_item.bytecode_offset += item.bytecode_offset
    return collapsed_items


def expand_items(items: CollapsedItems, is_linetable: bool) -> ExpandedItems:
    expanded_items = cast(ExpandedItems, [])
    MAX_BYTECODE = 254 if is_linetable else 255
    MIN_LINE = -127 if is_linetable else -128
    for item in items:
        line_offset = item.line_offset
        bytecode_offset = item.bytecode_offset
        emitted_extra = False

        def expand_bytecode():
            nonlocal bytecode_offset, line_offset, emitted_extra
            # While the bytecode offset is too large, emit the 0, 255 item
            while bytecode_offset > MAX_BYTECODE:
                expanded_items.append(
                    LineTableItem(
                        line_offset=(-128 if line_offset is None else line_offset)
                        if is_linetable
                        else 0,
                        bytecode_offset=MAX_BYTECODE,
                    )
                )
                if is_linetable:
                    line_offset = 0
                bytecode_offset -= MAX_BYTECODE
                emitted_extra = True

        def expand_line():
            nonlocal bytecode_offset, line_offset, emitted_extra
            # While the line offset is too large, emit the max line offset and remaining bytecode offset
            while line_offset is not None and line_offset > 127:
                expanded_items.append(
                    LineTableItem(
                        line_offset=127,
                        bytecode_offset=0 if is_linetable else bytecode_offset,
                    )
                )
                line_offset -= 127
                if not is_linetable:
                    bytecode_offset = 0
                emitted_extra = True

            # Same if its too small
            while line_offset is not None and line_offset < MIN_LINE:
                expanded_items.append(
                    LineTableItem(
                        line_offset=MIN_LINE,
                        bytecode_offset=0 if is_linetable else bytecode_offset,
                    )
                )
                line_offset -= MIN_LINE
                if not is_linetable:
                    bytecode_offset = 0
                emitted_extra = True

        if is_linetable:
            expand_line()
            expand_bytecode()
        else:
            expand_bytecode()
            expand_line()
        # If we have extra we haven't emited, add a last one.
        # Also emit a last one, even if we don't and we had a negative jump
        # (for some reason this always emits an extra jump)
        if line_offset != 0 or bytecode_offset != 0 or not emitted_extra:
            expanded_items.append(
                LineTableItem(
                    line_offset=-128 if line_offset is None else line_offset,
                    bytecode_offset=bytecode_offset,
                )
            )
    return expanded_items


def items_to_mapping(
    items: CollapsedItems, max_offset: int, is_linetable: bool
) -> LineMapping:
    offset_to_line: dict[int, Optional[int]] = {}
    offset_to_additional_line_offsets: dict[int, list[int]] = collections.defaultdict(
        list
    )
    current_item_offset = 0
    last_bytecode_offset = 0
    current_line = 0
    bytecode_offset = 0
    if is_linetable:
        for item in items:
            if item.line_offset is not None:
                current_line += item.line_offset
            for i in range(bytecode_offset, bytecode_offset + item.bytecode_offset, 2):
                offset_to_line[i] = None if item.line_offset is None else current_line
            bytecode_offset += item.bytecode_offset
        return LineMapping(offset_to_line, {})
    # Iterate through each bytecode offset and find the line number for it
    # Also, if our bytecode offset exceeds the max code offset, keep iterating
    # till our items are done, so that we include offsets for bytecode which
    # were eliminated during optimization
    while (bytecode_offset < max_offset) or current_item_offset < len(items):
        # if we haven't exhausted all the line table items
        if current_item_offset < len(items):
            # and the current bytecode offset difference is equal to the next line table
            # item difference, then advance the line table item.
            current_item = items[current_item_offset]
            if (bytecode_offset - last_bytecode_offset) == current_item.bytecode_offset:
                current_line += current_item.line_offset  # type: ignore
                current_item_offset += 1
                last_bytecode_offset = bytecode_offset

                # If the line_offset is 0, this is really a noop, so add to dict
                # to preserve isomporphism of this transform.
                # (only happens in Python <= 3.8 for things like `class A: pass\n class A: pass`)
                if current_item.line_offset == 0:
                    offset_to_additional_line_offsets[bytecode_offset].append(0)

            # special case for if the bytecode offset difference of this item is 0 and
            # this is not the first item.
            # If this is the case, then line changes should be recorded
            while (
                current_item_offset < len(items)
                and items[current_item_offset].bytecode_offset == 0
            ):
                line_offset = items[current_item_offset].line_offset
                offset_to_additional_line_offsets[bytecode_offset].append(line_offset)  # type: ignore
                current_item_offset += 1
                current_line += line_offset  # type: ignore
        # Otherwise save as the current line
        offset_to_line[bytecode_offset] = current_line
        bytecode_offset += 2

    return LineMapping(
        offset_to_line=offset_to_line,
        offset_to_additional_line_offsets=dict(offset_to_additional_line_offsets),
    )


def mapping_to_items(mapping: LineMapping, is_linetable: bool) -> CollapsedItems:
    items = cast(CollapsedItems, [])
    # The line table uses a different offset form, where the lines changed
    # are added at the end, instead of begining of a section
    if is_linetable:
        # The "section" is the group of lines with the same line number
        section_bytecode_offset = None
        section_line_number = None
        last_section_line_number = 0
        # This is the number of line numbers the section moved from the last
        section_line_number_diff = None
        for bytecode_offset, line_number in mapping.offset_to_line.items():
            # On first bytecode, this will be none
            if section_bytecode_offset is None:
                section_bytecode_offset = bytecode_offset
                section_line_number = line_number
                if line_number is not None:
                    last_section_line_number = line_number
                section_line_number_diff = line_number
            switching_sections = line_number != section_line_number
            # If we are switching sections, add the length
            # of the last section bytecode, and its line number diff
            if switching_sections:
                items.append(
                    CollapsedLineTableItem(
                        line_offset=section_line_number_diff,
                        bytecode_offset=bytecode_offset - section_bytecode_offset,
                    )
                )
                # the new section has begun!
                section_bytecode_offset = bytecode_offset
                # What's the diff from if the last one is None?
                # The diff is the difference between this section adn the last
                section_line_number_diff = (
                    None
                    if line_number is None
                    else line_number - last_section_line_number
                )
                section_line_number = line_number
                if line_number is not None:
                    last_section_line_number = line_number
        # If we added any bytecode, add a final section
        if bytecode_offset is not None:
            items.append(
                CollapsedLineTableItem(
                    line_offset=cast(int, section_line_number_diff),
                    bytecode_offset=bytecode_offset
                    + 2
                    - cast(int, section_bytecode_offset),
                )
            )
        return items

    last_line_number = 0
    last_bytecode_offset = 0

    for bytecode_offset, line_number in mapping.offset_to_line.items():
        additional_line_offsets = mapping.offset_to_additional_line_offsets.get(
            bytecode_offset, []
        )

        first_line_offset = (
            cast(int, line_number) - last_line_number - sum(additional_line_offsets)
        )

        # We should emit line offsets for each additional one, plus the first
        # if it is nonzero
        all_line_offsets = list(additional_line_offsets)
        if first_line_offset:
            all_line_offsets.insert(0, first_line_offset)
        # Emit a list of bytecode offsets
        for line_offset in all_line_offsets:
            items.append(
                CollapsedLineTableItem(
                    line_offset=line_offset,
                    bytecode_offset=bytecode_offset - last_bytecode_offset,
                )
            )
            last_bytecode_offset = bytecode_offset
        last_line_number = cast(int, line_number)

    return items
