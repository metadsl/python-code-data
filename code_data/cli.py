import argparse
import dis
import importlib.util
import pathlib
from os import linesep
from types import CodeType
from typing import Optional, cast

from rich.console import Console
from rich.syntax import Syntax

from . import CodeData, from_code_constant, from_code_data, to_code_data

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


def main():
    """
    Parse the CLI commands and print the code data.
    """
    args = parser.parse_args()
    file, cmd, mod, eval_, show_dis, show_source, show_dis_after = (
        args.file,
        args.c,
        args.m,
        args.e,
        args.dis,
        args.source,
        args.dis_after,
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
        dis.dis(code)
    code_data = to_code_data(code)
    console.print(code_data)
    if show_dis_after:
        dis.dis(from_code_data(code_data))
