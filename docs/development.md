# Development

## Creating environment

We use [pip-tools](https://github.com/jazzband/pip-tools) to pin all of our
development dependencies from reproducability accross development and CI.

To get started locally:

```bash
pip install -e . -r requirements.txt
```

If you local environment drifts from the pinned version, you can
also run `pip-sync` to make sure you have the right versions of
everything installed.

## Tests

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
