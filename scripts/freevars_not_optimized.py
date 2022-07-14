"""
Where are there freevars but the code object is not optimized?

7/14/2022
"""

import inspect
from collections import Counter
from types import CodeType

from code_data.module_codes import all_module_codes_cached

codes = all_module_codes_cached()


def freevars_not_optimized(code: CodeType) -> bool:
    return bool(code.co_freevars) and not (code.co_flags & inspect.CO_OPTIMIZED)


print(Counter(map(freevars_not_optimized, codes)))
# 243 which are tree

code = next(filter(freevars_not_optimized, codes))
# It's a class definition inside of a function, taking the args.
# except KeyError:
#     class CFunctionType(_CFuncPtr):
#         _argtypes_ = argtypes
#         _restype_ = restype
#         _flags_ = flags


def test():
    a = 100

    class B:
        x = a


import dis

dis.dis(test)


# OK what about when it is optimized and we have a LOAD_CLASSDEREF?
# This shows up in one edge case I believe in the LOAD_CLASSDEREF eval


def optimized_load_class_deref(code: CodeType) -> bool:
    return any(b.opname == "LOAD_CLASSDEREF" for b in dis.Bytecode(code)) and bool(
        code.co_flags & inspect.CO_OPTIMIZED
    )


print(Counter(map(optimized_load_class_deref, codes)))

# Ok this is never the case... so when does that piece of code get hit?
# It does get hit, see
# http://droettboom.com/cpython-coverage/Python/ceval.c.gcov.html#:~:text=3198%20%20%20%20%20%20%20%206049%20%3A%20%20%20%20%20%20%20%20%20%20%20%20%20if%20(!-,value,-)%20%7B%0A%20%20%20%203199%20%20%20%20%20%20%20%206048
