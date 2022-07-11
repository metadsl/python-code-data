from __future__ import annotations

from dataclasses import MISSING, fields
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import rich


class DataclassHideDefault:
    """
    Inherit from this class when creating a dataclass to not show any fields
    in the repr which are set to their default, with Rich.

    Also, any fields with `positional` metadata set to `True` will
    be shown as positional args.

    Refer to Rich reference for protocol:

    https://rich.readthedocs.io/en/stable/pretty.html
    """

    def __rich_repr__(self) -> rich.repr.Result:
        for f in fields(self):
            if not f.repr:
                continue
            if f.default_factory != MISSING:  # type: ignore
                default = f.default_factory()
            elif f.default != MISSING:
                default = f.default
            else:
                default = object()
            name = f.name
            value = getattr(self, f.name)
            if value == default:
                continue
            positional = f.metadata.get("positional", False)
            yield None if positional else name, value
