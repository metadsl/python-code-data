from __future__ import annotations

import sys
from dataclasses import dataclass, field
from itertools import chain
from types import CodeType
from typing import Iterator, Optional, Union

from pyparsing import line

__all__ = ["LineTable", "to_line_table", "from_line_table"]


def to_line_table(code: CodeType) -> LineTable:
    if sys.version_info >= (3, 10):
        return NewLineTable(code.co_linetable)  # type: ignore
    else:
        return OldLineTable.from_bytes(code.co_lnotab, code=code.co_code)


def from_line_table(line_table: LineTable) -> bytes:
    return line_table.to_bytes()


@dataclass
class NewLineTable:
    """
    PEP 626 line number table.
    https://www.python.org/dev/peps/pep-0626/
    """

    bytes_: bytes = field(default=b"")

    def to_bytes(self) -> bytes:
        return self.bytes_


@dataclass
class OldLineTable:
    """
    Pre PEP 626 line number mapping
    """

    # TODO: Make post verified items and pre verified -post
    items: list[LineTableItem] = field(default_factory=list)

    # TODO: move these inline into bytecode instructions
    bytecode_offset_to_line_number: dict[int, int] = field(default_factory=dict)
    # Mapping of bytecode offset to list of lines removed during compilation
    bytecode_offset_to_missing_lines_after: dict[int, list[int]] = field(
        default_factory=dict
    )

    post_items: list[LineTableItem] = field(default_factory=list)

    @classmethod
    def from_bytes(cls, bytes: bytes, code: bytes) -> OldLineTable:
        """
        Constructs a line table from a byte string.
        """
        items: list[LineTableItem] = []
        for i in range(0, len(bytes), 2):
            line_offset = bytes[i + 1]
            bytecode_offset = bytes[i]
            if bytecode_offset == 0 and items:
                items[-1].line_offset += line_offset
            else:
                items.append(
                    LineTableItem(
                        line_offset=line_offset, bytecode_offset=bytecode_offset
                    )
                )

        bytecode_offset_to_line_number: dict[int, int] = {}
        bytecode_offset_to_missing_lines_after: dict[int, tuple[int, int]] = {}

        current_item_offset = 0

        last_bytecode_offset = 0
        current_line = 1
        # Iterate through each bytecode offset and find the line number for it
        for bytecode_offset in range(0, len(code), 2):
            # If the bytecode offset is the same as the next offset
            if current_item_offset < len(items):
                current_item = items[current_item_offset]
                if (
                    bytecode_offset - last_bytecode_offset
                ) == current_item.bytecode_offset:
                    current_line += current_item.line_offset
                    current_item_offset += 1
                    last_bytecode_offset = bytecode_offset
            bytecode_offset_to_line_number[bytecode_offset] = current_line
        # If we have an item left over, this should have a 0 bytecode offset jump
        # and we store this in the remaining offset to lines after
        # if current_item_offset < len(items):
        #     # Verify its the last item we have left
        #     assert current_item_offset + 1  == len(items)
        #     item = items[current_item_offset]
        #     # Verify bytecode offset is 0
        #     assert item.bytecode_offset == 0
        #     bytecode_offset_to_missing_lines_after[bytecode_offset] = (current_line + 1, current_line + 1 + current_item.line_offset)

        post_items: list[LineTableItem] = []
        last_line_number = 1
        last_bytecode_offset = 0
        for bytecode_offset, line_number in bytecode_offset_to_line_number.items():
            # If the line changes, emit an item
            if line_number != last_line_number:
                line_offset = line_number - last_line_number
                bytecode_offset = bytecode_offset - last_bytecode_offset
                # additional_items = []
                # while line_offset > 127:
                #     additional_items.append(LineTableItem(line_offset=127, bytecode_offset=0))
                #     line_offset -= 127
                while line_offset:
                    written_line_offset = min(line_offset, 127)
                    written_bytecode_offset = bytecode_offset
                    line_offset -= written_line_offset
                    bytecode_offset -= written_bytecode_offset
                    post_items.append(
                        LineTableItem(
                            line_offset=written_line_offset,
                            bytecode_offset=written_bytecode_offset,
                        )
                    )
                # post_items.extend(additional_items)
                last_line_number = line_number
                last_bytecode_offset = bytecode_offset
            # if bytecode_offset in bytecode_offset_to_missing_lines_after:

        return OldLineTable(
            items,
            bytecode_offset_to_line_number=bytecode_offset_to_line_number,
            post_items=post_items,
            bytecode_offset_to_missing_lines_after=bytecode_offset_to_missing_lines_after,
        )

    def to_bytes(self) -> bytes:
        """
        Converts the line table to a byte string.
        """
        return bytes(chain.from_iterable(self.post_items))

    def verify(self):
        pass

    #     assert self.items == self.post_items


@dataclass
class LineTableItem:
    # TODO: Instead make mapping from bytecode offset to optinal line number
    # (but how to represent "missing lines"??) no change of bytecode, but line number change
    # means so line numbers were erased here
    # With another table of bytecode offset to missing lines added after!
    line_offset: int
    bytecode_offset: int

    def __iter__(self) -> Iterator[int]:
        yield self.bytecode_offset
        yield self.line_offset


LineTable = Union[NewLineTable, OldLineTable]
