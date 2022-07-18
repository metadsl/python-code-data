from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from inspect import _ParameterKind
from typing import Tuple

from . import Args, FlagsData


def args_from_input(input: ArgsInput) -> tuple[Args, FlagsData]:
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
        flags_data -= {"VARARGS"}
    else:
        var_positional = None

    keyword_only, varnames = (
        varnames[:kwonlyargcount],
        varnames[kwonlyargcount:],
    )
    if "VARKEYWORDS" in flags_data:
        var_keyword, varnames = varnames[0], varnames[1:]
        flags_data -= {"VARKEYWORDS"}
    else:
        var_keyword = None

    return (
        Args(
            positional_only=positional_only,
            positional_or_keyword=positional_or_keyword,
            var_positional=var_positional,
            keyword_only=keyword_only,
            var_keyword=var_keyword,
        ),
        flags_data,
    )


def args_to_input(args: Args, flags_data: FlagsData) -> ArgsInput:
    if args.var_positional:
        flags_data |= {"VARARGS"}
    if args.var_keyword:
        flags_data |= {"VARKEYWORDS"}
    return ArgsInput(
        argcount=len(args.positional_only) + len(args.positional_or_keyword),
        posonlyargcount=len(args.positional_only),
        kwonlyargcount=len(args.keyword_only),
        varnames=tuple(args.parameters.keys()),
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


def args_to_parameters(args: Args) -> OrderedDict[str, _ParameterKind]:
    return OrderedDict(
        (
            *((n, _ParameterKind.POSITIONAL_ONLY) for n in args.positional_only),
            *(
                (n, _ParameterKind.POSITIONAL_OR_KEYWORD)
                for n in args.positional_or_keyword
            ),
            *(
                ((args.var_positional, _ParameterKind.VAR_POSITIONAL),)
                if args.var_positional
                else ()
            ),
            *((n, _ParameterKind.KEYWORD_ONLY) for n in args.keyword_only),
            *(
                ((args.var_keyword, _ParameterKind.VAR_KEYWORD),)
                if args.var_keyword
                else ()
            ),
        )
    )
