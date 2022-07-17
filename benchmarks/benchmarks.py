import importlib.util

import code_data


class Suite:
    params = [
        "rich._emoji_codes",
    ]

    def setup(self, module_name):
        spec = importlib.util.find_spec(module_name)
        self.code = spec.loader.get_code(module_name)  # type: ignore
        self.code_data = code_data.CodeData.from_code(self.code)

    def teardown(self, module_name):
        del self.code, self.code_data

    def time_from_code(self, module_name):
        code_data.CodeData.from_code(self.code)

    def time_to_code(self, module_name):
        self.code_data.to_code()

    def time_equal(self, module_name):
        self.code_data == self.code_data

    def time_normalize(self, module_name):
        self.code_data.normalize()


if __name__ == "__main__":
    print("Benchmarking...")
    s = Suite()
    p = s.params[0]
    s.setup(p)
    s.time_to_code(p)
