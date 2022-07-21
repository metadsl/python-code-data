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

# Usage

## Python API

### `from_code`

The main entrypoint to our API is the `CodeData` object. You can create it from any Python `CodeType`:

```{code-cell}
# Load rich first for prettier output
from rich import pretty
pretty.install()
from code_data import CodeData

def fn(a, b):
    return a + b

cd = CodeData.from_code(fn.__code__)
cd
```

Instead of using Python's built in code object, or the `dis` module, it reduces the amoutn of information to only that which is needed to recreate the code object. So all information about how it happens to be stored on disk, the bytecode offsets for example of each instruction, is ommited, making it simpler to use.

### `normalize`

We are also able to "normalize" the code object, removing pieces of it that are unused. For example, if you have dead code, Python will still include the constants
that are present in it, even though there is no way they can be accessed:

```{code-cell}
def fn():
    if False:
        x = 20
    x = 1


cd = CodeData.from_code(fn.__code__)
cd
```

```{code-cell}
cd.normalize()
```

### JSON Support

Since the code object is now a simple data structure, we can serialize it to and from JSON. This provides a nice option if you want to analyze Python bytecode in a different language or save it on disk:

```{code-cell}
code_json = cd.to_json_data()
assert CodeData.from_json_data(code_json) == cd

code_json
```

## Command Line

We provide a CLI command `python-code-data` which is useful for debugging or introspecting code objects from the command line.

It contains many of the same
flags to load Python code as the default Python CLI, including from a string (`-c`),
from a module (`-m`), or from a path (`<file name>`). It also includes a way to
load a string from Python code to eval it first, which is useful for generating
test cases on the CLI of program strings.

```{code-cell}
! python-code-data -h
```

```{code-cell}
! python-code-data -c 'x if y else z'
```
