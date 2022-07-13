from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from inspect import _ParameterKind
from typing import Optional, Tuple

from code_data.flags_data import FlagsData

from .dataclass_hide_default import DataclassHideDefault


# TODO: Rename to parameters?
@dataclass(frozen=True)
class Args(DataclassHideDefault):
    """
    Holds the different possible args for a function
    """

    positional_only: tuple[str, ...] = field(default=())
    positional_or_keyword: tuple[str, ...] = field(default=())
    var_positional: Optional[str] = field(default=None)
    keyword_only: tuple[str, ...] = field(default=())
    var_keyword: Optional[str] = field(default=None)

    def parameters(self) -> OrderedDict[str, _ParameterKind]:
        """
        Returns the names of the args, in order, mapping to their kind.
        """
        return OrderedDict(
            (
                *((n, _ParameterKind.POSITIONAL_ONLY) for n in self.positional_only),
                *(
                    (n, _ParameterKind.POSITIONAL_OR_KEYWORD)
                    for n in self.positional_or_keyword
                ),
                *(
                    ((self.var_positional, _ParameterKind.VAR_POSITIONAL),)
                    if self.var_positional
                    else ()
                ),
                *((n, _ParameterKind.KEYWORD_ONLY) for n in self.keyword_only),
                *(
                    ((self.var_keyword, _ParameterKind.VAR_KEYWORD),)
                    if self.var_keyword
                    else ()
                ),
            )
        )

    def __len__(self) -> int:
        """
        Returns the number of args
        """
        return len(self.parameters())

    @classmethod
    def from_input(cls, input: ArgsInput) -> tuple[Args, FlagsData]:
        """
        Create args from code input, grabbing names in order from varnames.
        """
        argcount, posonlyargcount, kwonlyargcount, varnames, flags_data = (
            input.argcount,
            input.posonlyargcount,
            input.kwonlyargcount,
            input.varnames,
            input.flags_data,
        )

        positional_only, varnames = (
            varnames[:posonlyargcount],
            varnames[posonlyargcount:],
        )
        pos_or_kw_count = argcount - posonlyargcount
        positional_or_keyword, varnames = (
            varnames[:pos_or_kw_count],
            varnames[pos_or_kw_count:],
        )
        if "VARARGS" in flags_data:
            var_positional, varnames = varnames[0], varnames[1:]
        else:
            var_positional = None

        keyword_only, varnames = (
            varnames[:kwonlyargcount],
            varnames[kwonlyargcount:],
        )
        if "VARKEYWORDS" in flags_data:
            var_keyword, varnames = varnames[0], varnames[1:]
        else:
            var_keyword = None

        return (
            cls(
                positional_only=positional_only,
                positional_or_keyword=positional_or_keyword,
                var_positional=var_positional,
                keyword_only=keyword_only,
                var_keyword=var_keyword,
            ),
            flags_data,
        )

    def to_input(self, flags_data: FlagsData) -> ArgsInput:
        if self.var_positional:
            flags_data |= {"VARARGS"}
        if self.var_keyword:
            flags_data |= {"VARKEYWORDS"}
        return ArgsInput(
            argcount=len(self.positional_only) + len(self.positional_or_keyword),
            posonlyargcount=len(self.positional_only),
            kwonlyargcount=len(self.keyword_only),
            varnames=tuple(self.parameters().keys()),
            flags_data=flags_data,
        )


@dataclass
class ArgsInput:
    """
    Input to create the args from a code object.
    """

    # number of arguments (not including keyword only arguments, * or ** args)
    argcount: int
    # number of positional only arguments
    posonlyargcount: int
    # number of keyword only arguments (not including ** arg)
    kwonlyargcount: int
    # tuple of names of arguments and local variables
    varnames: Tuple[str, ...]
    # Initial flags data
    flags_data: FlagsData
