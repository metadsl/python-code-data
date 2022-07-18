import subprocess


def test_help_runs():
    subprocess.check_call(["python-code-data", "--help"])


def test_string():
    subprocess.check_call(["python-code-data", "-c", "x = y"])


def test_file():
    subprocess.check_call(["python-code-data", __file__])


def test_module():
    subprocess.check_call(["python-code-data", "-m", "code_data"])


def test_print_source():
    subprocess.check_call(["python-code-data", "-c", "x = y", "--source"])
