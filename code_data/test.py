from __future__ import annotations

import pathlib
import warnings

import hypothesmith
from hypothesis import HealthCheck, given, settings
from pytest import mark, param

from .test_verify_code import verify_code

NEWLINE = "\n"
EXAMPLES = [
    param("\n", id="blank"),
    param("a", id="variable"),
    param("class A: pass\nclass A: pass\n", id="duplicate class"),
    param(f"x = 1{NEWLINE * 127}\ny=2", id="long line jump"),
    # https://bugs.python.org/msg26661
    param(
        f'x = x or {"-x" * 100}\nwhile x:\n    x -= 1',
        id="long jump",
    ),
    # Reduced from imagesize module
    # https://bugs.python.org/issue46724
    # negative opargs in Python 3.10
    param("while not x < y < z:\n    pass", id="bpo-46724"),
    param(
        "y =" + ("-x" * 100) + ("\n" * 300) + "z = y",
        id="long line and bytecode jump",
    ),
    param("f(\n1)", id="negative line jump"),
    param("f(" + "\n" * 256 + "1)", id="long negative jump"),
    param(
        """def _():
    return
    return
""",
        id="multiple returns",
    ),
    param("_ = 0j", id="complex"),
    # param("class G: pass\n" * 1006, id="many classes"),
    param(
        """
def fn():
    return
    def i():
        i()
""",
        id="unused cellvar",
    ),
]
# Read all test files from directory
EXAMPLES_DIR = pathlib.Path(__file__).parent / "test_minimized"
EXAMPLES += [
    param(path.read_text(), id=path.stem) for path in EXAMPLES_DIR.glob("*.py")
]


@mark.parametrize("source", EXAMPLES)
def test_examples(source):
    code = compile(source, "<string>", "exec")

    verify_code(code)


@given(source_code=hypothesmith.from_node())
@settings(
    suppress_health_check=(HealthCheck.filter_too_much, HealthCheck.too_slow),
    deadline=None,
)
def test_generated(source_code):
    with warnings.catch_warnings():
        # Ignore syntax warnings in compilation
        warnings.simplefilter("ignore")
        code = compile(source_code, "<string>", "exec")
    verify_code(code)
