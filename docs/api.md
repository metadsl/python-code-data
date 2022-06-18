# API

At the top level, we can convert to and from code data:

```{eval-rst}
.. autofunction:: code_data.code_to_data
.. autoclass:: code_data.code_data.CodeData
```

Inside the blocks of the `CodeData`, is a list of `Instructions`:

```{eval-rst}
.. autoclass:: code_data.blocks.Instruction
.. autoclass:: code_data.blocks.Jump
```

The line table is currently stored in either the old or new format, changed in Python 3.10:

```{eval-rst}
.. autoclass:: code_data.line_mapping.LineMapping
```
