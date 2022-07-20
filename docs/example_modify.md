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

# Example: Modifying Existing Bytecode

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
