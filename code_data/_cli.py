import argparse
import dis
import importlib.util
import pathlib
from os import linesep
from types import CodeType
from typing import Optional, cast

try:
    from rich.console import Console
    from rich.syntax import Syntax
except ImportError:
    # If we can't import rich, just create dummy classes which use the basic printing
    class Console:  # type: ignore
        def print(self, *args, **kwargs):
            print(*args, **kwargs)

    def Syntax(source, language, line_numbers=False):  # type: ignore
        return source


from code_data._normalize import normalize

from . import CodeData

__all__ = ["main"]

parser = argparse.ArgumentParser(description="Inspect Python code objects.")
parser.add_argument("file", type=pathlib.Path, nargs="?", help="path to Python program")
parser.add_argument("-c", type=str, help="program passed in as string", metavar="cmd")
parser.add_argument(
    "-e", type=str, help="string evalled to make program", metavar="eval"
)
parser.add_argument("-m", type=str, help="python library", metavar="mod")
parser.add_argument("--dis", action="store_true", help="print Python's dis analysis")
parser.add_argument(
    "--dis-after",
    action="store_true",
    help="print Python's dis analysis after round tripping to code-data, for testing",
)
parser.add_argument("--source", action="store_true", help="print the source code")
parser.add_argument(
    "--no-normalize",
    action="store_true",
    help="don't normalize code data before printing",
)


# TODO: #51 Add tests for CLI
def main():
    """
    Parse the CLI commands and print the code data.
    """
    args = parser.parse_args()
    file, cmd, mod, eval_, show_dis, show_source, show_dis_after, no_normalize = (
        args.file,
        args.c,
        args.m,
        args.e,
        args.dis,
        args.source,
        args.dis_after,
        args.no_normalize,
    )

    if len(list(filter(None, [file, cmd, mod, eval_]))) != 1:
        parser.error("Must specify exactly one of file, cmd, eval, or mod")

    console = Console()
    source: Optional[str]
    code: CodeType
    if eval_ is not None:
        source = eval(eval_, {"linesep": linesep})
        code = compile(cast(str, source), "<string>", "exec")
    elif file is not None:
        source = file.read_text()
        code = compile(cast(str, source), str(file), "exec")
    elif cmd is not None:
        # replace escaped newlines with newlines
        source = cmd.replace("\\n", "\n")
        code = compile(source, "<string>", "exec")  # type: ignore
    elif mod is not None:
        spec = importlib.util.find_spec(mod)
        assert spec
        assert spec.loader
        code = spec.loader.get_code(mod)  # type: ignore
        source = spec.loader.get_source(mod)  # type: ignore
        assert code

    if show_source and source is not None:
        console.print(Syntax(source, "python", line_numbers=True))
    if show_dis:
        show_code_recursive(code)
        dis.dis(code)
    code_data = CodeData.from_code(code)
    if not no_normalize:
        code_data = normalize(code_data)
    console.print(code_data)
    if show_dis_after:
        res = code_data.to_code()
        show_code_recursive(res)
        dis.dis(res)


def show_code_recursive(code: CodeType):
    dis.show_code(code)
    # Print newline
    print("")
    for c in code.co_consts:
        if isinstance(c, CodeType):
            show_code_recursive(c)
