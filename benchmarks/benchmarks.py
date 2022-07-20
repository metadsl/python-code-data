import pathlib
from copy import deepcopy

import code_data


class Suite:
    params = ["rich._emoji_codes", "numpy.core.tests.test_multiarray"]
    # Run each benchmark at least 5 times to get a good average
    min_run_count = 5

    def setup(self, module_name):
        path = (
            pathlib.Path(__file__).parent.parent
            / "code_data"
            / "_test_minimized"
            / f"{module_name}.py"
        )
        self.code = compile(path.read_text(), str(path), "exec")
        self.code_data = code_data.CodeData.from_code(self.code)
        self.copy_code_data = deepcopy(self.code_data)
        self.json_data = self.code_data.to_json_data()

    def teardown(self, module_name):
        del self.code, self.code_data, self.json_data

    def time_from_code(self, module_name):
        code_data.CodeData.from_code(self.code)

    def time_to_code(self, module_name):
        self.code_data.to_code()

    def time_equal(self, module_name):
        self.code_data == self.copy_code_data

    def time_normalize(self, module_name):
        self.code_data.normalize()

    def time_to_json_data(self, module_name):
        self.code_data.to_json_data()

    def time_from_json_data(self, module_name):
        code_data.CodeData.from_json_data(deepcopy(self.json_data))


if __name__ == "__main__":
    print("Benchmarking...")
    s = Suite()
    p = s.params[1]
    s.setup(p)
    s.time_to_code(p)
