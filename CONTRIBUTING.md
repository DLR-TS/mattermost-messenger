# Contributing

## How to contribute

To contribute you may

* Create an issue if you have found a bug or if you have an idea for an improvement or other change.
* Create a pull request to contribute a change.
  * The pull request should not break existing tests unless they introduce a change that contradicts existing tests. In that case adapt the tests.
  * If meaningful, add tests for the changed code.



## Building




### Python Poetry

The Mattermost Messenger applies [Python Poetry](https://python-poetry.org/) for package management. If you haven't done that yet, you need to install it with

```bash
pip install poetry
```

Next you need to apply Poetry to create a virtual environment with the required dependencies for the following steps with

```bash
poetry install
```


### Build package

To create the Mattermost Messenger package file call

```bash
poetry build
```

This creates a subfolder `dist` with a `.whl` file.


### Install built package

After the last step the subfolder `dist` contains a file `mattermost_messenger-<version>-py3-none-any.whl` with `<version>` as placeholder for the current version (from `pyproject.toml`). You can install it with `pip` into any Python environment to import the package or execute the command line tool as described below.


### `pyproject.toml`

File `pyproject.toml` is the configuration file for building the package. It contains mainly some metadata and the dependencies.



## Coding guidelines

### Naming

Use CamelCase and *no* underscores except the leading underscore as private marker.

Class and type names should start with a capital character, anything else with a non-capital character.

Consider to mark any attribute and method as private by a leading underscore that should not be used by the user of a class.


### Typing

It is strongly recommended to add types to all function parameters, to their return values, and to global variables. Adding types to class attributes and local variables may also be helpful to prevent bugs. The types will also be part of the auto-generated API documentation.


### Dependencies

Currently, the code itself does not have any dependencies on non-standard Python packages. However, testing and building the documentation requires some additional packages.

If you contribute code try to stick to the standard Python library to avoid additional dependencies. If not possible, add it to the section `[tool.poetry.dependencies]` in `pyproject.toml` and update the building instructions accordingly.

Additional testing or documentation dependencies have to be added to sections `[tool.poetry.group.test.dependencies]` or `[tool.poetry.group.docs.dependencies]` respectively.


### Documentation

All classes, functions, methods, global variables, etc. should have a docstring. The API reference documentation in the HTML documentation is generated from the docstrings by applying [Sphinx AutoAPI](https://sphinx-autoapi.readthedocs.io/en/latest/index.html). See `README.md` on how to do that easily with Poetry.

Please use the [Sphinx docstring format](https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html#the-sphinx-docstring-format) in the docstrings to describe parameters, return value, etc. for functions. Note that docstrings for global variables need to be put *after* the variable definition.

General documentation pages can be added in ReStructured Text or Markdown format to the `docs` folder. Add them to `index.rst` to make them available. Markdown will be converted to ReStructured Text with [MyST](https://myst-parser.readthedocs.io), which also allows to embed ReStructured Text directives in Markdown.

The documentation is configured in `docs/conf.py`.


### Unit tests

There should be unit tests for any function and class method to test at least the major functionality including error handling. See following section about testing for details.



## Testing

Dependencies for running the test tools are contained in the dependency group `test`. To install the testing tools into the Poetry venv call

```bash
poetry install --with=test
```


### Unit tests

Subdir `tests` contains Python unit test. To run them all, call:

```bash
poetry run pytest .
```

Many tests still make use of the `unittest` package and its features, which are supported by `pytest` as well. Newer tests may use `pytest` features directly.


### Type checks

For type checking apply [my[py]](https://mypy.readthedocs.io/en/stable/) to the code:

```bash
poetry run mypy .
```


