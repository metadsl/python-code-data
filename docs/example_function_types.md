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

# Example: Functions argument types

In this example, we are going to see what types of arguments are most popular in Python.

First, let's pull in all the code from every module we can import:

```{code-cell}
from code_data.module_codes import modules_codes_cached

# tuples of name, source, code
module_codes = modules_codes_cached()
print(f"We have loaded {len(module_codes)} modules")
```

Now we can turn them all into data, and also iterate through them all to have all the recursive
ones at the top level:

```{code-cell}
from code_data import to_code_data

all_code_data = {code_data for _, _, code in module_codes for code_data in to_code_data(code)}
print(f"We have loaded {len(all_code_data)} code data objects")
```

Let's filter for functions:

```{code-cell}
from code_data import FunctionBlock

fns = {c for c in all_code_data if isinstance(c.type, FunctionBlock)}
print(f"{len(fns)} of them are functions")
```

We can see how many functions have a docstring:

```{code-cell}
from collections import Counter

have_docstring = Counter(bool(f.type.docstring) for f in fns)

print(f"The function has a docstring? {have_docstring}")
```

And finally, we can see how many different argument types are used cumulatively:

```{code-cell}
param_kinds = Counter(k for c in fns for k in c.type.args.parameters().values())
param_kinds
```

There are an order of magnitude more "positional or keyword" arguments then all other
types combined!

And we can see there is the least number of positional only arguments, which make
sense since they were most recently introduced in [PEP 570](https://peps.python.org/pep-0570/)
