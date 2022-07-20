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

# Example: Analyzing instruction occurances

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
from code_data import CodeData

all_code_data = [CodeData.from_code(code) for (name, source, code) in names_source_and_codes]
all_code_data[0].flags
```

We can see that the flags are a list of strings.

Now let's analyze all of them to see which flags are most popular!

```{code-cell}
from collections import defaultdict, Counter

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
