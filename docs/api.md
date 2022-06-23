# API

At the top level, we can convert a CodeType to and from code data:

```{eval-rst}
.. autofunction:: code_data.to_code_data
.. autofunction:: code_data.from_code_data
```

THe `CodeData` is a data class which contains the same information to reconstruct
the Python CodeType, but is easier to deal with, then the bytecode pieces in there:

```{eval-rst}
.. autoclass:: code_data.CodeData
```

Inside the blocks of the `CodeData`, is a list of `Instructions`:

```{eval-rst}
.. autoclass:: code_data.blocks.Instruction
.. autoclass:: code_data.blocks.Jump
```

It also includes a `LineMapping` for additional line information:

```{eval-rst}
.. autoclass:: code_data.line_mapping.LineMapping
```
