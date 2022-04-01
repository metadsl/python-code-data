# Development

To setup locally, we have a `requirements.txt` pinned with all of the development
depenencies:

```bash
pip install -e .[docs,test]
```

To run the the tests:

```bash
mypy code_data/
pytest code_data
```

## Pre-commit

We use pre-commit to run some linting. To run these on all files:

```bash
pre-commit run --all
```

## Docs

We build the docs using Jupyter Book on Read The Docs. This should just work,
but if you update the docs config, you have to update the `conf.py` file with
`pre-commit`.

To build the book locally:

```bash
$ jupyter-book build docs
$ open docs/_build/html/index.html
```

Note that this may take a while, since it re-executes the notebooks.
