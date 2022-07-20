# Learnings about `CodeType`

_I wanted to start collecting my learning about the code object, as I created this library. Unfortunately, I had this idea after I was mostly done, so it is by no means complete._

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

### Are all the code with arguments "functions"? i.e. do they have the `NEWLOCALS` and `OPTIMIZED` flags?

Yes all code data with args are functions!

## `co_freevars` and `co_cellvars`

If we look in `dis` we see that any of the "hasfree" commands will index into `cell_names = co.co_cellvars + co.co_freevars`.

The ones marked as using it are:

- `LOAD_CLOSURE`
- `LOAD_DEREF`
- `STORE_DEREF`
- `DELETE_DEREF`
- `LOAD_CLASSDEREF`

Let's take a look at `ceval.c` to see where they are used.

`LOAD_CLASSDEREF` is the clearest, in that it requires the arg to index into `co_freevars`
and be larger than `co_cellvars`.

The rest all index into `freevars` directly, which is defined as `f->f_localsplus + co->co_nlocals`.

This `f_localsplus` contains both the `varnames` locals plus the cells and freevars.
And since `nlocals == len(varnames)`, this offsets the array to start looking at the
cellvars and freevars. This is created in `PyFrame_FastToLocalsWithError` in `frameobject.c`.
