# Development

## Creating environment

To get started locally:

```bash
pip install -e . -r requirements.dev.txt
```

## Tests

To run the the tests:

```bash
mypy code_data/
pytest code_data
```

## pip-tools

We use [pip-tools](https://github.com/jazzband/pip-tools) to pin all of our
development dependencies from reproducability accross development and CI.

We keep three different sets of requirement files:

1. `requirements.test.txt` - includes all test requirements. Installable on all supported
   Python versions. Used by CI to run tests and locally when creating different environments
   for different Python versions.
2. `requirements.docs.txt` - includes all doc requirements. Installable on latest supported Python version.
   Used by CI to buildcreate the docs.
3. `requirements.txt` - includes all development, test, and docs requirements. Installable on latest supported version. Used locally to setup a development environment with all test, doc, and lint tools.

We split out test and docs requirements into separate files to make installing them in CI
faster, and also to reduce the chance of conflict dependent on Python versions. For examples,
some of our dev requirements require different incompatbile versions of dependencies depending
on the Python version we are installing under. Bu splitting them out, we can reduce the
chance of a conflict by only requiring the minimal number of test dependencies to be compatible
with all Python versions. We don't test docs and linting on multiple Python versions, only
the code.

All of these files are kept up to date via pre-commit hooks that are run in CI.

If you local environment drifts from the pinned version, you can
also run `pip-sync` to make sure you have the right versions of
everything installed.

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

## Benchmarking

We have some benchmarks setup with [airspeed-velocity](https://github.com/airspeed-velocity/asv).

If you are working on a branch and want to compare performance against main, you can run:

```shell
$ pip install asv
$ asv continuous origin/main HEAD
```

Also, we can run the benchmarks in CI to compare a pull request against the main branch.
To do so, add a commit with `!benchmark` in the commit message. This will trigger a
workflow that will run the benchmarks and you can inspect the results of the workflow
run to see the benchmark results.


## Releasing

We use a Github Action, which can be manually triggerd, along with [`bump2version`](https://github.com/c4urself/bump2version)
to release new versions of the package.

To trigger run the [release workflow](https://github.com/metadsl/python-code-data/actions/workflows/release.yml) which will prompt you to choose a level to bump based on the [semver](https://semver.org/) of the unreleased changes in the [changelog](./CHANGELOG.md):

![Screen Shot 2022-10-11 at 10 57 21 AM](https://user-images.githubusercontent.com/1186124/195127045-de23dadb-b445-49e1-8f14-d5db41d18b84.png)
