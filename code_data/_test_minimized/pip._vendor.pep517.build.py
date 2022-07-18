"""Build a project using PEP 517 hooks.
"""
import argparse
import io
import logging
import os
import shutil

from .compat import FileNotFoundError, toml_load
from .dirtools import mkdir_p, tempdir
from .envbuild import BuildEnvironment
from .wrappers import Pep517HookCaller

log = logging.getLogger(__name__)


def validate_system():
    pass


def load_system():
    pass


def compat_system():
    pass


def _do_build():
    pass


def build(system=None):
    pass


parser = argparse.ArgumentParser()
parser.add_argument(
    "source_dir",
    help="A directory containing pyproject.toml",
)
parser.add_argument(
    "--binary",
    "-b",
    action="store_true",
    default=False,
)
parser.add_argument(
    "--source",
    "-s",
    action="store_true",
    default=False,
)
parser.add_argument(
    "--out-dir",
    "-o",
    help="Destination in which to save the builds relative to source dir",
)


def main(args):
    pass


if __name__ == "__main__":
    main(parser.parse_args())
