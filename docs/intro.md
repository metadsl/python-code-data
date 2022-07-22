---
jupytext:
  cell_metadata_filter: -all
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.11.5
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# Intro

`python-code-data` is a Python package which provides a way to convert a Python
"code object" into data that can be introspected and changed. It provides
a higher level API than manipulating code objects directly, but faithfully
maintains the full semantics of the code object for Python 3.7-3.10.

- Tested to make sure the `CodeData` object is isomorphic to the original
  code object on all installed modules and using generative testing with Hypothesis (using [hypothesmith](https://github.com/Zac-HD/hypothesmith#hypothesmith) to generate Python code).
- Decodes flags and bytecode into a human readable form.
- Hashable, just like the original code object.
- Provides a CLI to introspect Python objects from the command line, with
  colored pretty printing courtesy of Rich.
- Able to encode to/from JSON faithfully

It is meant to be used by anyone trying to understand Python code to build some sort of compiler, for tools like Numba.

First install the package, alongside rich for pretty printing:

```bash
pip install python-code-data[rich]
```

Then try inspecting some code objects:

```{code-cell}
# 1. Install rich hooks for prettier printing
from rich import pretty
pretty.install()


# 2. Get a code object
def fn(x):
    y = x + 1
    return y


# 3. Convert it to a dataclass!
from code_data import CodeData

CodeData.from_code(fn.__code__)
```
