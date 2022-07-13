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

### Example: Modifying Existing Bytecode

In this example, we will compile some code, modify the bytecode, and then turn it back into Python code to execute.

We can make a code object from a string using `compile`:

```{code-cell}
x = True
source_code = "print(10 + (100 if x else 10))"
code = compile(source_code, "", "exec")
exec(code)
```

If we look at the code object, we can see that it does have the bytecode, but its represented as byte string, which isn't very helpful:

```{code-cell}
print(code)
print(code.co_code)
```

We could use Python's built in `dis` module to introspect the code object. This is helpful to look at it, but won't let us change it:

```{code-cell}
import dis
dis.dis(code)
```

So instead, lets turn it into ✨data✨:

```{code-cell}
from code_data import CodeData

code_data = CodeData.from_code(code)
code_data
```

This is still a bit hard to see, so let's install Rich's pretty print helper:

```{code-cell}
from rich import pretty
pretty.install()
code_data
```

That's better!

We can see now that we have two blocks, each with a list of instructions.

Let's try to change the additions to subtractions!

```{code-cell}
from dataclasses import replace

new_code_data = replace(
    code_data,
    blocks=tuple(tuple(
        replace(instruction, name="BINARY_SUBTRACT") if instruction.name == "BINARY_ADD" else instruction
        for instruction in block
    ) for block in code_data.blocks)
)
```

Now we can turn this back into code and exec it!

```{code-cell}
new_code = new_code_data.to_code()
exec(new_code)
```

### Example: Analyzing instruction occurances

For our next example, lets do something a bit more fun. Let's load all installed modules and see what flags are most commonly used!n Let's
sort the flags by what "level" they were defined at. For example, a module is
at the top level, a class second level, etc.

First we can load all the code objects for all importable modules, using
a util written for the tests. In the tests, we use this to verify that
our code analysis is isomporphic, meaning that when we convert to and from the
code data, we should get back an equivalent code object.

```{code-cell}
from code_data.module_codes import modules_codes_cached

names_source_and_codes = modules_codes_cached()
names_source_and_codes[:3]
```

Lets turn them all into code data:

```{code-cell}
all_code_data = [CodeData.from_code(code) for (name, source, code) in names_source_and_codes]
all_code_data[0].flags
```

We can see that the flags are a list of strings.

Now let's analyze all of them to see which flags are most popular!

```{code-cell}
from collections import defaultdict, Counter
from code_data import CodeData

# Mapping from each level index to a counter of the flags
flags_per_level = defaultdict(Counter)
counts_per_level = defaultdict(lambda: 0)

def process_code_data(code_data: CodeData, level: int) -> None:
    flags_per_level[level].update(code_data.flags)
    counts_per_level[level] += 1
    for c in code_data:
        process_code_data(c, level + 1)

for code_data in all_code_data:
    process_code_data(code_data, 0)

(counts_per_level, flags_per_level)
```

We can see that every top level code object has `NOFREE` set, but that isn't the case
with some of the nested modules. We can also see one code object is nested six levels!

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
