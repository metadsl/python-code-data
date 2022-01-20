
from .code_data import CodeData
from types import CodeType
__version__ = "0.0.0"

__all__ = ["CodeData", "CodeType"]

def code_to_data(code: CodeType) -> CodeData:
   '''
   Parse a code type and turn it into data.
   '''
   return CodeData.from_code(code)