"""
Are any cellvars out of place?
"""

from rich import pretty

from code_data import Cellvar, CodeData
from code_data.module_codes import all_module_code_data_cached

pretty.install()

cd = all_module_code_data_cached()


def cellvars_out_of_place(code: CodeData) -> bool:
    return any(
        instruction.arg._index_override is not None
        for block in code.blocks
        for instruction in block
        if isinstance(instruction.arg, Cellvar)
    )


print(any(map(cellvars_out_of_place, cd)))

next(filter(cellvars_out_of_place, cd))

# Yes there are some
