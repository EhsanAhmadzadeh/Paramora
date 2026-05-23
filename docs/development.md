# Development with uv

Paramora is developed uv-first.

## Install dependencies

```bash
uv sync --group dev
```

## Run tests

```bash
uv run pytest -vv
```

Optional backend integration dependencies are not required for normal
development. To run the full integration suite, install the integration group:

```bash
uv sync --group dev --group integration
uv run pytest -vv
```

## Run the quality gate

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -vv
```

## Format code

```bash
uv run ruff format .
uv run ruff check --fix .
```

## Packaging policy

The wheel should contain the runtime `paramora` package and type marker. The
source distribution can include tests, docs, benchmarks, and contributor files.
Docs stay in the main branch so links from the README, PyPI, and GitHub remain
stable.
