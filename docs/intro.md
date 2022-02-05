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

## FAQ

Q: How is this diferent from Python's built in [`dis` bytecode analysis](https://docs.python.org/3/library/dis.html#bytecode-analysis)?

A: Like `dis`, `code_data` provides a way to understand Python's code objects at a higher level. They both map the bytes of the bytecode to instructions. `code_data`, however also provides a way to go back to the bytecode, from the high level description, unlike `dis`. This isomorphism makes it easy to test that the transformation to and from `code_data` preserves the original bytecode semantics, by verifying the resulting bytecode is equal to the initial.

It's focus is also slightly different. While `dis` is meant to help aid in debugging bytecode, `code_data` is meant to be the first step in compiling Python or doing automated program analysis. Therefore, it is meant to abstract away from the details of how bytecode is persisted in memory. For example, you can't see the offset of each instruction in `code_data`, like you can with `dis`. So in this way, `code_data` actually provides *less* information, prefering to only preserve the high level semantics and not the underlying storage represenation. This is intentional, to make it simpler to understand what parts of the data are relevent. For example, with the `dis` module, to do block analysis, you might wonder if it's important at all to know the underlying bytecode offset of an instruction, because that information is included in the `dis.Instruction` instance. With `code_data`, it is not provided, so you know it's safe to ignore.

## Background

The goal of this package is to present an alternative representation of Python
that is more amenable to analysis and optimization. The eventual goal is to
lift Python's bytecode into an SSA form and then transforming that SSA
CFG into a dataflow graph, and this package is the first step along that path.

It mirrors in some way the work in the C / LLVM space to automatically parallize
and optimize that code.

One way we can understand this problem is visually, as the number of differnt
forms Python takes:

1. In the **CPython** implementation, Python goes from:
   1. **Source code**
   2. to an **AST**
   3. to **bytecode**
2. We then want to take that lowest level, bytecode, and build back up to a higher level representation
   that is more amenable to optimization and analysis, describing the semantics of Python:
   1. This package implements a **minimal data semantics of the bytecode** level, that is more tightly specified
     than how the bytecode is represented in memory. This gives us a higher 
     level representation
   2. On top of that, we can transform the stack based representation into **SSA CFG** created from the bytecode. This effectively erases the stack details, leaving you with SSA. This translation is meant to be an
     abstract analog of CPython's bytecode interpreter. So that instead of 
     interpreting the bytecode eagerly, it builds up a CFG first that has the
     same semantics as interpreting it.
   3. Finally, we can lift that A dataflow graph, showing data dependencies, from this SSA. At this level,
     program optimization becomes much simpler and straightforward.

We test out abstraction level 1-3 by also building ways to go backwards, and
taking Python bytecode as an input and making sure all the transformations are
isomorphic. This type of testing can help us be confident that the different
representations are semantically faithful to the original bytecode source, and
so the original Python behavior.

To use this library to somehow optimize or analyze Python code then, you would
walk down the first three Python levels, then walk down our three levels we
provide here, perform any optimizations or translations, and walk back up
however many levels you like to get the form you are looking for. 

The underlying theory behind this library is that at the dataflow graph level,
we can more closely represent the programs denotional semantics, aka the
underlying conceptual meaning of the program. This is the level closer to our
own human understanding of what the program "does". So if we can move the
program faithfully up to this level, then we can reason about it in terms which
are closer to how we think.

For example, as a human we can reason about adding taking the sum of two
arrays, and say that "the result at index i is the addition of the first array
at index i at the second array at index i. So if we add two arrays and then
immediately index, we know that we don't have to recompute the full array, but
simply the sum of the two corresponding values." Encoding this sort of logic at
the level of Python bytecode simply does not make sense. The bytecode has no
idea about some abstract value of an array, or more fundamentally even of a
value that is defined mathematically like this. However, at the dataflow level,
it becomes feasible to reason about values in this matheamtical sense, instead
of in a memory/imperative sense. So at least we have some hope of being express
this sort of meaning, and have the computer use it to optimize our program.

After doing this optimization,  we can move it back down to whatever level we
like to actually execute. We might chose to go back to Python source, or we
might instead chose to compile to some alternative implementaiton before
executing, such as high level language like SQL or a lower level langauge like
LLVM.
