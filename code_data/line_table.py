from __future__ import annotations

import sys
from dataclasses import dataclass, field
from itertools import chain
from types import CodeType
from typing import Iterator, Union

__all__ = ["LineTable", "to_line_table", "from_line_table"]


def to_line_table(bytes_: bytes = b"") -> LineTable:
    if sys.version_info >= (3, 10):
        return NewLineTable(bytes_)  # type: ignore
    else:
        return OldLineTable.from_bytes(bytes_)


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

    items: list[LineTableItem] = field(default_factory=list)
    # TODO: Build line table properly!
    @classmethod
    def from_bytes(cls, bytes: bytes) -> OldLineTable:
        """
        Constructs a line table from a byte string.
        """
        items = []
        for i in range(0, len(bytes), 2):
            items.append(LineTableItem(bytes[i + 1], bytes[i]))
        return OldLineTable(items)

    def to_bytes(self) -> bytes:
        """
        Converts the line table to a byte string.
        """
        return bytes(chain.from_iterable(self.items))


@dataclass
class LineTableItem:
    line_offset: int
    bytecode_offset: int

    def __iter__(self) -> Iterator[int]:
        yield self.bytecode_offset
        yield self.line_offset


LineTable = Union[NewLineTable, OldLineTable]
