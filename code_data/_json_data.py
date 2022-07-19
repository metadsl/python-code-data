from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import fields, is_dataclass

from . import (
    AdditionalLine,
    Arg,
    Args,
    Cellvar,
    CodeData,
    Constant,
    ConstantBool,
    ConstantComplex,
    ConstantEllipsis,
    ConstantFloat,
    ConstantInt,
    ConstantSet,
    ConstantTuple,
    Freevar,
    FunctionBlock,
    Instruction,
    Jump,
    Name,
    Varname,
)
from ._constants import to_constant
from .dataclass_hide_default import field_is_default

##
# to json
##


def code_data_to_json(code_data: CodeData) -> dict:
    res = value_to_json(code_data)
    if not isinstance(res, dict):
        raise ValueError(f"Expected dict, got {type(res)}")
    return res


def value_to_json(value: object) -> object:
    """
    Like as dict but removes fields which are their defaults
    """
    if isinstance(value, ConstantEllipsis):
        return {"type": "ellipsis"}
    if isinstance(value, ConstantComplex):
        return {"real": value.value.real, "imag": value.value.imag}
    if isinstance(value, bytes):
        return {"bytes": b64encode(value).decode("ascii")}
    # Unwrap constants
    if isinstance(
        value,
        (
            ConstantBool,
            ConstantFloat,
            ConstantInt,
            ConstantSet,
            ConstantTuple,
        ),
    ):
        return value_to_json(value.value)
    if is_dataclass(value):
        return {
            f.name: (
                # Special case flags, so they are not wrapped in a "frozenset" type
                # We don't need to store this in JSON.
                list(getattr(value, f.name))
                if f.name == "flags"
                else value_to_json(getattr(value, f.name))
            )
            for f in fields(value)
            if not field_is_default(f, value)
        }
    if isinstance(value, tuple):
        return list(map(value_to_json, value))
    if isinstance(value, frozenset):
        return {"frozenset": list(map(value_to_json, value))}
    if isinstance(value, (int, float, str, type(None))):
        return value
    raise NotImplementedError(f"Unsupported value type: {type(value)}")


##
# from json
##


def code_data_from_json(value: object) -> CodeData:
    """
    Parse a JSON value into a CodeData object.
    """
    if not isinstance(value, dict):
        raise ValueError(f"Expected dict, got {type(value)}")
    if "blocks" in value:
        value["blocks"] = tuple(
            tuple(instruction_from_json(i) for i in block) for block in value["blocks"]
        )
    if "type" in value:
        tp = value["type"]
        if "args" in tp:
            tp["args"] = Args(**lists_values_to_tuples(tp["args"]))
        value["type"] = FunctionBlock(**tp)
    if "flags" in value:
        value["flags"] = frozenset(value["flags"])
    if "_additional_args" in value:
        value["_additional_args"] = tuple(
            arg_from_json(a) for a in value["_additional_args"]
        )
    if "_additional_line" in value:
        value["_additional_line"] = AdditionalLine(
            **lists_values_to_tuples(value["_additional_line"])
        )
    return CodeData(**lists_values_to_tuples(value))


def lists_values_to_tuples(d):
    """
    Converts all list values to tuples
    """
    return {k: tuple(v) if isinstance(v, list) else v for k, v in d.items()}


def instruction_from_json(value: object) -> Instruction:
    """
    Parse a JSON value into an instruction.
    """
    if not isinstance(value, dict):
        raise ValueError(f"Expected dict, got {type(value)}")
    value["arg"] = arg_from_json(value["arg"])
    return Instruction(**lists_values_to_tuples(value))


def arg_from_json(value: object) -> Arg:
    """
    Parse a JSON value into an argument.
    """
    if isinstance(value, int):
        return value
    if not isinstance(value, dict):
        raise ValueError(f"Expected dict, got {type(value)}")
    if "target" in value:
        return Jump(**value)
    if "name" in value:
        return Name(**value)
    if "varname" in value:
        return Varname(**value)
    if "constant" in value:
        if isinstance(value["constant"], dict) and "filename" in value["constant"]:
            value["constant"] = code_data_from_json(value["constant"])
        else:
            value["constant"] = to_constant(constant_value_from_json(value["constant"]))
        return Constant(**value)
    if "freevar" in value:
        return Freevar(**value)
    if "cellvar" in value:
        return Cellvar(**value)
    raise ValueError(f"Unsupported arg type: {type(value)}")


def constant_value_from_json(value: object) -> object:
    """
    Parse a JSON value into a Python value for a constant.
    """
    if isinstance(value, dict):
        if "type" in value and value["type"] == "ellipsis":
            return ...
        if "real" in value:
            return complex(value["real"], value["imag"])
        if "bytes" in value:
            return b64decode(value["bytes"])
        if "frozenset" in value:
            return frozenset(map(constant_value_from_json, value["frozenset"]))
    if isinstance(value, list):
        return tuple(map(constant_value_from_json, value))
    if isinstance(value, (bool, str, int, float, type(None))):
        return value

    raise NotImplementedError(f"Unsupported constant: {value}")
