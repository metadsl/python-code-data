# Learnings

_I wanted to start collecting my learning about the code object, as I created this library. Unfortunately, I had this idea after I was mostly done, so it is by no means complete._

## Python's Code object

Fields:

## `co_varnames`

This is the list of local variables names. It is accessed in the evaluation loop by `LOAD_FAST`, `DELETE_FAST`, and `STORE_FAST`.

### Are all the `co_varnames` used by these operations? Or is it important to save unused `co_varnames` so they get copied to the frame and used in some other way?

Not every co_varname is used. Most codes actually included unused varnames!

This is because these are used for the function arguments. It also includes the local variables...
Weird they are put in the same one!

We cannot eliminate unused ones. That is actually [enforced during bytecode creation](https://github.com/python/cpython/blob/817414321c236a77e05c621911d6f694db1262e2/Objects/codeobject.c#L185-L197), to make sure we have enough `co_varnames` for the args.

### Are all `co_varnames` after the argument names used in the code?

Mostly yes. The only place they don't get used is if they are optimized away, like in a `if False: ...` block. So we
can safely remove all the unused varnames, which are not arguments.
