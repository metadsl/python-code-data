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

The overall workflow for using the API involves some part of these steps:

1. Get your hands on a [Code object](https://docs.python.org/3/reference/datamodel.html#index-55), like by using `compile`
2. Turn it into data using .
3. Modify it, traverse it, or use it for downstream analysis.
4. Turn the [`CodeData`](code_data.CodeData) back into a real Python code object.
5. Execute the code object, using `exec`.

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
