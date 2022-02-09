# Development

To setup locally, we have a `requirements.txt` pinned with all of the development
depenencies:

```bash
pip install -r requirements.txt
```

To run the the tests:

```bash
mypy code_data/
```

## Pre-commit

We use pre-commit to run some linting. To run these on all files:

```bash
pre-commit run --all
```

## Requirements

We use [pip-tools](https://github.com/jazzband/pip-tools) to create a pinned
requirements file. This makes sure that CI and development have a consistant
environment.

If you add a new dependency, run `pip-compile` to update the `requirements.txt`
and then run `pip-sync` to update your environment with it:

```bash
pip-compile requirements.in
pip-sync
```

To upgrade any pinned dependencies, run:

```bash
pip-compile requirements.in --upgrade --strip-extras
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
