from __future__ import annotations

import rich.progress
from pytest import mark, param

from .module_codes import module_codes
from ._test import EXAMPLES_DIR
from ._test_verify_code import verify_code

MODULES = list(module_codes())

# Pass in index of module as argument and use name as ID
PARAMS = [param(i, id=module[0]) for i, module in enumerate(MODULES)]


@mark.parametrize("i", PARAMS)
def test_module(i: int) -> None:
    """
    Test all modules we can import
    """
    name, source, code = MODULES[i]

    succeeded = False
    try:
        verify_code(code)
        succeeded = True
    except KeyboardInterrupt:
        succeeded = True
        raise
    finally:
        if not succeeded:
            # When a test fails, minify the failure and save it to the file.
            minimize_failure(name, source)


def minimize_failure(name: str, source: str):
    """
    When a module fails to pass, find a minimal failing source code
    and save it as an example to easily retry it later.
    """
    lines = source.splitlines()
    with rich.progress.Progress(
        *rich.progress.Progress.get_default_columns(),
        rich.progress.TimeElapsedColumn(),
        rich.progress.MofNCompleteColumn(),
        rich.progress.TransferSpeedColumn(),
    ) as progress:

        # Try to do a simple minimization of the failure by removing lines
        # from the end until it passes
        for i in progress.track(
            list(reversed(range(1, len(lines)))),
            description="Trimming end lines",
        ):
            minimized_source = "\n".join(lines[:i])
            # If we can't compile, then skip this source
            try:
                code = compile(minimized_source, "", "exec")
            except Exception:
                continue
            else:
                try:
                    verify_code(code, debug=False)
                # If this fails, its the new minimal source
                except Exception:
                    source = minimized_source
                # Otherwise, if it passes, we trimmed too much, we are done
                else:
                    break
        lines = source.splitlines()
        for i in progress.track(
            list(range(1, len(lines))),
            description="Trimming begining lines",
        ):
            minimized_source = "\n".join(lines[i:])
            # If we can't compile, then skip this source
            try:
                code = compile(minimized_source, "", "exec")
            except Exception:
                continue
            else:
                try:
                    verify_code(code, debug=False)
                # If this fails, its the new minimal source
                except Exception:
                    source = minimized_source
                # Otherwise, if it passes, we trimmed too much, we are done
                else:
                    break
    path = EXAMPLES_DIR / f"{name}.py"
    path.write_text(source)
    progress.console.print(f"Wrote minimized source to {path}")
    code = compile(source, str(path), "exec")
