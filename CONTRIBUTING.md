# Contributing

## Development setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Running tests

```sh
python3 -m pytest
```

## Linting

This project uses [ruff](https://docs.astral.sh/ruff/) for Python linting and
[markdownlint](https://github.com/DavidAnson/markdownlint) for Markdown files.

```sh
ruff check .
```

## Pull requests

- Keep changes focused and add tests for new behaviour.
- Make sure `ruff check .` and `python3 -m pytest` both pass before opening a PR.
- CI runs both automatically on every push and pull request.
