# `python-code-data`

`python-code-data` is a Python package which provides a way to convert a Python
"code object" into data that can be introspected and changed. It provides
a higher level API than manipulating code objects directly, but faithfully
maintains the full semantics of the code object for Python 3.7-3.10.

- Tested to make sure the `CodeData` object is isomorphic to the original
  code object on all builtin modules and using generative testing with Hypothesis.
- Decodes flags and bytecode into a human readable form.
- Provides a CLI to introspect Python objects from the command line, with
  colored pretty printing courtesy of Rich.


It is meant to be used by anyone trying to understand Python code to build some sort of compiler, for tools like Numba.

## Usage

```bash
$ python-code-data
usage: python-code-data [-h] [-c cmd] [-e eval] [-m mod] [--dis] [--dis-after]
                        [--source]
                        [file]

Inspect Python code objects.

positional arguments:
  file         path to Python program

options:
  -h, --help   show this help message and exit
  -c cmd       program passed in as string
  -e eval      string evalled to make program
  -m mod       python library
  --dis        print Python's dis analysis
  --dis-after  print Python's dis analysis after round tripping to code-data,
               for testing
  --source     print the source code
$ python-code-data -c 'x if y else z'
CodeData(
    flags_data={'NOFREE'},
    cfg=[
        [
            Instruction(name='LOAD_NAME', arg=0),
            Instruction(name='POP_JUMP_IF_FALSE', arg=Jump(target=1)),
            Instruction(name='LOAD_NAME', arg=1),
            Instruction(name='POP_TOP', arg=0),
            Instruction(name='LOAD_CONST', arg=0),
            Instruction(name='RETURN_VALUE', arg=0)
        ],
        [Instruction(name='LOAD_NAME', arg=2), Instruction(name='POP_TOP', arg=0), Instruction(name='LOAD_CONST', arg=0), Instruction(name='RETURN_VALUE', arg=0)]
    ],
    names=('y', 'x', 'z'),
    line_table=NewLineTable(bytes_=b'\x14\x00')
)
```

## Development

```bash
pip install flit
flit install --symlink

mypy code_data/
pytest code_data/
```


