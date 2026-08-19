# Contributing to rtfreporter (Python)

Thanks for your interest in improving `rtfreporter`.  This is a focused,
opinionated toolkit for one clinical TFL house style — contributions that keep
that scope small and the RTF output faithful are the most welcome.

## Development setup

Create a virtual environment **outside** any slow network/bind mount, then
install in editable mode with the dev extras:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev,docs]"
```

## Running the checks

```bash
ruff check .          # lint
pytest -q             # tests
mkdocs build          # docs build (must succeed with no errors)
```

`pytest -q` must be green before you open a pull request.

## Guidelines

- **Faithful RTF semantics matter most.** When porting behaviour from the R
  package, match the emitted RTF tokens rather than the exact R API.
- **Test the output structure, not brittle whole-file equality.** Assert on the
  presence/shape of RTF tokens (`\trowd`, `\cellx`, `\clbrdrb`, …).
- **Type hints and docstrings** on every public symbol; snake_case, dataclasses.
- Keep the public surface documented in `docs/` and exported from
  `rtfreporter/__init__.py`.

## Reporting issues

Please include the input data, the code you ran, and either the generated RTF
or a description of how it renders in your word processor.

## Code of Conduct

Be kind and constructive.  We follow the spirit of the
[Contributor Covenant](https://www.contributor-covenant.org/).
