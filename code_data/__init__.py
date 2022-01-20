from types import CodeType

from .code_data import CodeData

__version__ = "0.0.0"

__all__ = ["CodeData", "CodeType"]


def code_to_data(code: CodeType) -> CodeData:
    """
    Parse a code type and turn it into data.
    """
    return CodeData.from_code(code)
