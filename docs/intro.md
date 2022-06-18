# Intro

`python-code-data` is a Python package which provides a way to convert a Python
"code object" into data that can be introspected and changed. It provides
a higher level API than manipulating code objects directly, but faithfully
maintains the full semantics of the code object for Python 3.7-3.10.

- Tested to make sure the `CodeData` object is isomorphic to the original
  code object on all builtin modules and using generative testing with Hypothesis (using [hypothesmith](https://github.com/Zac-HD/hypothesmith#hypothesmith) to generate Python code).
- Decodes flags and bytecode into a human readable form.
- Provides a CLI to introspect Python objects from the command line, with
  colored pretty printing courtesy of Rich.

It is meant to be used by anyone trying to understand Python code to build some sort of compiler, for tools like Numba.
