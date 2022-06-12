from __future__ import annotations

import dis
import pathlib
import pkgutil
import sys
import warnings
from datetime import timedelta
from dis import _get_instructions_bytes  # type: ignore
from importlib.abc import Loader
from types import CodeType
from typing import Iterable

import hypothesmith
import pytest
import rich.progress
from hypothesis import HealthCheck, given, settings

from code_data.line_table import (
    LineMapping,
    bytes_to_items,
    collapse_items,
    expand_items,
    items_to_bytes,
    items_to_mapping,
    mapping_to_items,
)

from .code_data import CodeData

NEWLINE = "\n"


def module_file(name):
    return pathlib.Path(__file__).parent / "code_data_test_minimized" / f"{name}.py"


def module_param(name):
    """
    Create an example param for a minimized failing test case of a module
    """
    return pytest.param(module_file(name).read_text(), id=f"minimized {name}")


EXAMPLES = [
    pytest.param("\n", id="blank"),
    pytest.param("a", id="variable"),
    pytest.param("class A: pass\nclass A: pass\n", id="duplicate class"),
    module_param("json.scanner"),
    pytest.param(f"x = 1{NEWLINE * 127}\ny=2", id="long line jump"),
    # https://bugs.python.org/msg26661
    pytest.param(
        f'x = x or {"-x" * 100}\nwhile x:\n    x -= 1',
        id="long jump",
    ),
    # Tests for a relative jump which has extended args
    module_param("notebook.tests.test_config_manager"),
    module_param("pip._vendor.pep517.build"),
    # Reduced from imagesize module
    # https://bugs.python.org/issue46724
    # negative opargs in Python 3.10
    pytest.param("while not x < y < z:\n    pass", id="bpo-46724"),
    pytest.param(
        "y =" + ("-x" * 100) + ("\n" * 300) + "z = y",
        id="long line and bytecode jump",
    ),
    pytest.param("f(\n1)", id="negative line jump"),
    pytest.param("f(" + "\n" * 256 + "1)", id="long negative jump"),
    pytest.param(
        r"""def _():
    return
    return
""",
        id="multiple returns",
    ),
    module_param("appnope._dummy"),
    module_param("turtledemo.minimal_hanoi"),
    module_param("idlelib.idle_test.test_hyperparser"),
    module_param("astroid.brain.brain_numpy_ndarray"),
    module_param("sphinx_comments"),
    module_param("pre_commit.languages.r"),
    module_param("setuptools.config"),
]


@pytest.mark.parametrize("source", EXAMPLES)
def test_examples(source):
    code = compile(source, "<string>", "exec")

    verify_code(code)


def test_modules():
    # Instead of params, iterate in test so that:
    # 1. the number of tests is consistant accross python versions pleasing xdist running multiple versions
    # 2. pushing loading of all modules inside generator, so that fast samples run first

    # Keep a list of failures, so we can print the shortest at the end
    # list of (name, source) tuples
    failures: list[tuple[str, str]] = []

    with rich.progress.Progress() as progress:
        modules = track_unknown_length(progress, module_codes(), "1. Loading modules")

        for name, source, code in progress.track(
            modules, description="2. Testing module"
        ):
            try:
                verify_code(code)
            except Exception as e:
                failures.append((name, source))
                progress.console.print(f"[red]{name} failed")

        if failures:
            # sort failures by length of source
            name, source = sorted(failures, key=lambda failure: len(failure[1]))[0]
            lines = source.splitlines()
            # Try to do a simple minimization of the failure by removing lines from the end
            # until it passes
            for i in progress.track(
                list(reversed(range(1, len(lines)))),
                description=f"3. Minimizing failure {name}",
            ):
                minimized_source = "\n".join(lines[:i])
                # If we can't compile, then skip this source
                try:
                    code = compile(minimized_source, "", "exec")
                except Exception:
                    progress.console.print("Can't compile")
                    continue
                else:
                    try:
                        verify_code(code)
                    # If this fails, its the new minimal source
                    except Exception as e:
                        error = e
                        source = minimized_source
                        progress.console.print("New minimal source")
                    # Otherwise, if it passes, we trimmed too much, we are done
                    else:
                        progress.console.print("Trimmed too much")
                        break
            module_file(name).write_text(source)
            progress.console.print(f"Add example: module_param({repr(name)})")
            assert False


@given(source_code=hypothesmith.from_node())
@settings(
    suppress_health_check=(HealthCheck.filter_too_much, HealthCheck.too_slow),
    deadline=timedelta(
        milliseconds=1000
    ),  # increase deadline to account for slow times in CI
)
def test_generated(source_code):
    with warnings.catch_warnings():
        # Ignore syntax warnings in compilation
        warnings.simplefilter("ignore")
        code = compile(source_code, "<string>", "exec")
    verify_code(code)


def module_codes() -> Iterable[tuple[str, str, CodeType]]:
    # In order to test the code_data, we try to get a sample of bytecode,
    # by walking all our packages and trying to load every module.
    # Note that although this doesn't require the code to be executable,
    # `walk_packages` does require it, so this will ignore any modules
    # which raise errors on import.

    with warnings.catch_warnings():
        # Ignore warning on find_module which will be deprecated in Python 3.12
        # Worry about it later!
        warnings.simplefilter("ignore")
        for mi in pkgutil.walk_packages(onerror=lambda _name: None):
            loader: Loader = mi.module_finder.find_module(mi.name)  # type: ignore
            try:
                code = loader.get_code(mi.name)  # type: ignore
            except SyntaxError:
                continue
            if code:
                source = loader.get_source(mi.name)  # type: ignore
                yield mi.name, source, code


def verify_code(code: CodeType) -> None:
    # First verify the line mapping is accurate
    verify_line_mapping(code)

    code_data = CodeData.from_code(code)
    code_data._verify()
    resulting_code = code_data.to_code()

    # First compare as primitives, for better diffing if they aren't equal
    assert code_to_primitives(code, verify_line_mappings=True) == code_to_primitives(
        resulting_code, verify_line_mappings=False
    )

    # Then compare objects directly, for greater equality confidence
    assert code == resulting_code
    # We used to compare the marhsalled bytes as well, but this was unstable
    # due to whether the constants had refernces to them, so we disabled it


code_attributes = tuple(
    name
    for name in dir(CodeType)
    if name.startswith("co_")
    # Don't compare generated co_lines iterator returned in Python 3.10
    # When co_lntob is removed in 3.12, we need to figured out how to adapt.
    # TODO: look at how co_lines works and make sure we can duplicate logic for mapping
    # https://docs.python.org/3/whatsnew/3.10.html?highlight=co_lines#pep-626-precise-line-numbers-for-debugging-and-other-tools
    and name != "co_lines"
)


def code_to_primitives(code: CodeType, verify_line_mappings: bool) -> dict[str, object]:
    """
    Converts a code object to primitives, for better pytest diffing.

    Also verifies that line mapping are accurate for each
    """
    if verify_line_mappings:
        verify_line_mapping(code)
    return {
        name: (
            # Recursively transform constants
            tuple(
                code_to_primitives(a, verify_line_mappings)
                if isinstance(a, CodeType)
                else a
                for a in getattr(code, name)
            )
            # Compare code with instructions for easier diff
            if name == "co_consts"
            else [(i.opname, i.argval) for i in _get_instructions_bytes(code.co_code)]
            if name == "co_code"
            else getattr(code, name)
        )
        for name in code_attributes
    }


def code_to_dict(code: CodeType) -> dict[str, object]:
    """
    Converts a code object to a dict for testing
    """
    return {name: getattr(code, name) for name in dir(code)}


def verify_line_mapping(code: CodeType):
    """
    Verify the mapping type by testing each conversion layer and making sure they
    are isomorphic.

    The tests are written in this way, so we can more easily which layer is causing the error.
    """
    # Include when we need to show locals
    _dis = dis.Bytecode(code).dis()
    # print(_dis)

    b = code.co_lnotab
    max_offset = len(code.co_code)
    expanded_items = bytes_to_items(b)
    assert items_to_bytes(expanded_items) == b, "bytes to items to bytes"

    collapsed_items = collapse_items(expanded_items)
    assert (
        expand_items(collapsed_items) == expanded_items
    ), "collapsed to expanded to collapsed"

    mapping = items_to_mapping(collapsed_items, max_offset)
    assert mapping_to_items(mapping) == collapsed_items, "items to mapping to items"

    assert mapping_to_line_starts(mapping, code.co_firstlineno, max_offset) == dict(
        dis.findlinestarts(code)
    ), "mapping matches dis"


def mapping_to_line_starts(
    mapping: LineMapping, first_line_number: int, length_code: int
) -> dict[int, int]:
    """
    Convert our mapping to a dis line starts output to verify our implementation.
    """
    line_starts_dict: dict[int, int] = {}

    last_line = None
    for bytecode, line in mapping.offset_to_line.items():
        # If we are past the end of the code, don't add anymore
        # dis does not include these, after 37
        if sys.version_info >= (3, 8) and bytecode >= length_code:
            break
        if line != last_line:
            line_starts_dict[bytecode] = line + (first_line_number)
            last_line = line
    return line_starts_dict


def track_unknown_length(progress, iterable, description):
    """
    Version of Rich's track which supports iterable's of unknown length.
    """
    t = progress.add_task(description, total=None)
    l = []
    for x in iterable:
        progress.update(t, advance=1)
        l.append(x)

    return l
