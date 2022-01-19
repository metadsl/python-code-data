# Development


We use flit for packaging, which you can also use to setup a development environment locally:

```bash
pip install flit
flit install --symlink
```

To run the the tests and mypy:

```
mypy code_data/
pytest code_data/
```


We build the docs using Jupyter Book on Read The Docs. This should just work,
but if you update the docs config, you have to update the `conf.py` file with
`pre-commit`.
