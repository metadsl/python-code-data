"""
Counts the number of duplciate code values in each block, to see if there
is a lot of extra memory used by inlining the constants.

Works on 7/8/2022
"""

from __future__ import annotations

import collections

from code_data import CodeData
from code_data._blocks import Constant
from code_data.module_codes import module_codes

code_counts = collections.Counter[int]()


def traverse(code_data: CodeData) -> None:
    code_data_counts = collections.Counter[CodeData]()
    for block in code_data.blocks:
        for instruction in block:
            if isinstance(instruction.arg, Constant) and isinstance(
                instruction.arg.value, CodeData
            ):
                sub_code_data = instruction.arg.value
                code_data_counts[sub_code_data] += 1
                traverse(sub_code_data)
    code_counts.update(code_data_counts.values())


print("Loading modules...")
for name, _, code in module_codes():
    print(name)
    traverse(CodeData.from_code(code))

print("Counts of duplicate code values", code_counts)
