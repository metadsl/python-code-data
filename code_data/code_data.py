from __future__ import annotations

import sys
from types import CodeType

from . import CodeData, FunctionBlock
from .args import ArgsInput, args_from_input, args_to_input
from .blocks import blocks_to_bytes, bytes_to_blocks
from .constants import from_constant, to_constant
from .flags_data import from_flags_data, to_flags_data
from .line_mapping import from_line_mapping, to_line_mapping

# Functions should have both of these flags set
# https://github.com/python/cpython/blob/443370d8acd107da235d2e9758e06ab3583be4ea/Python/compile.c#L5348
FN_FLAGS = {"NEWLOCALS", "OPTIMIZED"}


def to_code_data(code: CodeType) -> CodeData:

    if sys.version_info >= (3, 8):
        posonlyargcount = code.co_posonlyargcount
    else:
        posonlyargcount = 0

    line_mapping = to_line_mapping(code)

    # TODO: #54 For functions, do 1 + this line
    first_line_number_override = line_mapping.set_first_line(code.co_firstlineno)

    constants = tuple(map(to_constant, code.co_consts))

    flags_data = to_flags_data(code.co_flags)

    args, flags_data = args_from_input(
        ArgsInput(
            argcount=code.co_argcount,
            posonlyargcount=posonlyargcount,
            kwonlyargcount=code.co_kwonlyargcount,
            varnames=code.co_varnames,
            flags_data=flags_data,
        )
    )

    # TODO: Make this special type constructor?
    fn_flags = flags_data & FN_FLAGS
    if len(fn_flags) == 0:
        block_type = None
        assert not args, "if this isn't a function, it shouldn't have args"
    elif len(fn_flags) == 2:
        # Use the first const as a docstring if its a string
        # https://github.com/python/cpython/blob/da8be157f4e275c4c32b9199f1466ed7e52f62cf/Objects/funcobject.c#L33-L38
        docstring = (
            constants[0] if constants and isinstance(constants[0], str) else None
        )
        block_type = FunctionBlock(args, docstring)
        flags_data -= FN_FLAGS
    else:
        raise ValueError(f"Expected both flags to represent function: {fn_flags}")

    # retrieve the blocks and pop off used line mapping
    (
        blocks,
        additional_names,
        additional_varnames,
        additional_constants,
    ) = bytes_to_blocks(
        code.co_code,
        line_mapping,
        code.co_names,
        code.co_varnames,
        code.co_freevars,
        code.co_cellvars,
        constants,
        block_type,
        args,
    )
    next_line = line_mapping.pop_additional_line(len(code.co_code))
    return CodeData(
        blocks,
        next_line,
        first_line_number_override,
        additional_names,
        additional_varnames,
        additional_constants,
        block_type,
        code.co_freevars,
        code.co_stacksize,
        flags_data,
        code.co_filename,
        code.co_name,
    )


def from_code_data(code_data: CodeData) -> CodeType:

    flags_data = code_data.flags
    if isinstance(code_data.type, FunctionBlock):
        flags_data = flags_data | FN_FLAGS
    (code, line_mapping, names, varnames, cellvars, constants) = blocks_to_bytes(
        code_data.blocks,
        code_data._additional_names,
        code_data._additional_varnames,
        code_data._additional_constants,
        code_data.freevars,
        code_data.type,
    )

    consts = tuple(map(from_constant, constants))

    if code_data._additional_line:
        line_mapping.add_additional_line(code_data._additional_line, len(code))

    if isinstance(code_data.type, FunctionBlock):
        args_input = args_to_input(code_data.type.args, flags_data)
        argcount = args_input.argcount
        posonlyargcount = args_input.posonlyargcount
        kwonlyargcount = args_input.kwonlyargcount
        flags_data = args_input.flags_data

        assert (
            varnames[: len(args_input.varnames)] == args_input.varnames
        ), "varnames should start with args"
    else:
        argcount = 0
        posonlyargcount = 0
        kwonlyargcount = 0

    flags = from_flags_data(flags_data)

    first_line_no = line_mapping.trim_first_line(code_data._first_line_number_override)

    line_table = from_line_mapping(line_mapping)
    nlocals = len(varnames)
    freevars = code_data.freevars
    # https://github.com/python/cpython/blob/cd74e66a8c420be675fd2fbf3fe708ac02ee9f21/Lib/test/test_code.py#L217-L232
    # Only include posonlyargcount on 3.8+
    if sys.version_info >= (3, 8):
        return CodeType(
            argcount,
            posonlyargcount,
            kwonlyargcount,
            nlocals,
            code_data.stacksize,
            flags,
            code,
            consts,
            names,
            varnames,
            code_data.filename,
            code_data.name,
            first_line_no,
            line_table,
            freevars,
            cellvars,
        )
    else:
        if posonlyargcount:
            raise NotImplementedError(
                "Positional only args are only supported on Python 3.8+"
            )
        return CodeType(
            argcount,
            kwonlyargcount,
            nlocals,
            code_data.stacksize,
            flags,
            code,
            consts,
            names,
            varnames,
            code_data.filename,
            code_data.name,
            first_line_no,
            line_table,
            freevars,
            cellvars,
        )
