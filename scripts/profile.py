import importlib.util

import code_data

print("Loading code...")
module_name = "test.datetimetester"
spec = importlib.util.find_spec(module_name)
code = spec.loader.get_code(module_name)  # type: ignore


print("Loading code data")
cd = code_data.CodeData.from_code(code)
# print("saving code data")
# cd.to_code()
