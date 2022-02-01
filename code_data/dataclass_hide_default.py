from dataclasses import MISSING, fields


class DataclassHideDefault:
    """
    Inherit from this class when creating a dataclass to not show any fields
    in the repr which are set to their default, with Rich.

    Also, any fields with `positional` metadata set to `True` will
    be shown as positional args.

    Refer to Rich reference for protocol:

    https://rich.readthedocs.io/en/stable/pretty.html
    """

    def __rich_repr__(self):
        for f in fields(self):
            if not f.repr:
                continue
            if f.default_factory is not MISSING:
                default = f.default_factory()
            elif f.default is not MISSING:
                default = f.default
            else:
                default = object()
            name = f.name
            value = getattr(self, f.name)
            if value == default:
                continue
            if f.metadata.get("positional", False):
                yield value
            else:
                yield name, value
