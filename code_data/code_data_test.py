from __future__ import annotations

import pkgutil
import warnings
from datetime import timedelta
from dis import _get_instructions_bytes  # type: ignore
from importlib.abc import Loader
from types import CodeType
from typing import Iterable

import hypothesmith
import pytest
from hypothesis import HealthCheck, given, settings

from .code_data import CodeData

NEWLINE = "\n"


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("a", id="variable"),
        pytest.param("class A: pass\nclass A: pass\n", id="duplicate class"),
        pytest.param(
            """def _scan_once(string, idx):
    try:
        nextchar = string[idx]
    except IndexError:
        raise StopIteration(idx) from None

    if nextchar == '"':
        return parse_string(string, idx + 1, strict)
    elif nextchar == "{":
        return parse_object(
            (string, idx + 1),
            strict,
            _scan_once,
            object_hook,
            object_pairs_hook,
            memo,
        )
    elif nextchar == "[":
        return parse_array((string, idx + 1), _scan_once)
    elif nextchar == "n" and string[idx : idx + 4] == "null":
        return None, idx + 4
    elif nextchar == "t" and string[idx : idx + 4] == "true":
        return True, idx + 4
    elif nextchar == "t" and string[idx : idx + 4] == "true":
        return True, idx + 4""",
            id="json.scanner",
        ),
        pytest.param(f"x = 1{NEWLINE * 127}\ny=2", id="long line jump"),
        # https://bugs.python.org/msg26661
        pytest.param(
            """
def f(x):
    %s
    %s
    %s
    %s
    %s
    %s
    %s
    %s
    %s
    %s
    while x:
        x -= 1
        # EXTENDED_ARG/JUMP_ABSOLUTE here
    return x
"""
            % (("x = x or " + "-x" * 2500,) * 10),
            id="long jump",
        ),
        pytest.param("""import json

def test_json():
    tmpdir = tempfile.mkdtemp()
    try:
        root_data = dict(a=1, x=2, nest={'a':1, 'x':2})
        with open(os.path.join(tmpdir, 'foo.json'), 'w') as f:
            json.dump(root_data, f)
        # also make a foo.d/ directory with multiple json files
        os.makedirs(os.path.join(tmpdir, 'foo.d'))
        with open(os.path.join(tmpdir, 'foo.d', 'a.json'), 'w') as f:
            json.dump(dict(a=2, b=1, nest={'a':2, 'b':1}), f)
        with open(os.path.join(tmpdir, 'foo.d', 'b.json'), 'w') as f:
            json.dump(dict(a=3, b=2, c=3, nest={'a':3, 'b':2, 'c':3}, only_in_b={'x':1}), f)
        manager = BaseJSONConfigManager(config_dir=tmpdir, read_directory=False)
        data = manager.get('foo')
        assert 'a' in data
        assert 'x' in data
        assert 'b' not in data
        assert 'c' not in data
        assert data['a'] == 1
        assert 'x' in data['nest']
        # if we write it out, it also shouldn't pick up the subdirectory
        manager.set('foo', data)
        data = manager.get('foo')
        assert data == root_data

        manager = BaseJSONConfigManager(config_dir=tmpdir, read_directory=True)
        data = manager.get('foo')
        assert 'a' in data
        assert 'b' in data
        assert 'c' in data
        # files should be read in order foo.d/a.json foo.d/b.json foo.json
        assert data['a'] == 1
        assert data['b'] == 2


    finally:
        pass""", id="notebook.tests.test_config_manager minimal case")
    ],
)
def test_examples(source):
    code = compile(source, "<string>", "exec")

    verify_code(code)


def test_modules(subtests):
    # Instead of params, iterate in test so that:
    # 1. the number of tests is consistant accross python versions pleasing xdist running multiple versions
    # 2. pushing loading of all modules inside generator, so that fast samples run first

    # Keep a list of failures, so we can print the shortest at the end
    # list of (name, source) tuples
    failures: list[tuple[str, str]] = []
    
    for name, source, code in module_codes():
        failures.append((name, source))
        with subtests.test(name):
            verify_code(code)
            # If we got here, then the verification succeeded, and we can remove from failures.
            failures.pop()
    
    if failures:
        # sort failures by length of source
        name, source = sorted(failures, key=lambda failure: len(failure[1]))[0]
        print(source)
        assert False, f"Shortest module that failed was {name}"


@given(source_code=hypothesmith.from_node())
@settings(
    suppress_health_check=(HealthCheck.filter_too_much, HealthCheck.too_slow),
    deadline=timedelta(
        milliseconds=400
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
            loader.__ne__
            try:
                code = loader.get_code(mi.name)  # type: ignore
            except SyntaxError:
                continue
            if code:
                source = loader.get_source(mi.name) #type: ignore
                yield mi.name, source, code


def verify_code(code: CodeType) -> None:
    code_data = CodeData.from_code(code)
    code_data.verify()
    resulting_code = code_data.to_code()

    # First compare as primitives, for better diffing if they aren't equal
    assert code_to_primitives(code) == code_to_primitives(resulting_code)

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


def code_to_primitives(code: CodeType) -> dict[str, object]:
    """
    Converts a code object to primitives, for better pytest diffing
    """
    return {
        name: (
            # Recursively transform constants
            tuple(
                code_to_primitives(a) if isinstance(a, CodeType) else a
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
