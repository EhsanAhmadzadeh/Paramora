# Development with uv

Paramora is developed uv-first. The repository includes helper scripts so local
workflows match CI as closely as possible.

## Install dependencies

Install the full development environment, including backend test dependencies and
documentation tooling:

```bash
uv sync --group dev --group docs
```

The development group intentionally installs optional backend libraries such as
`mongomock`, `sqlalchemy`, `sqlmodel`, `psycopg`, `beanie`, and `mongoengine`.
This keeps the local test suite representative of the package features.

## Local quality gate

Run everything before opening a pull request:

```bash
scripts/check.sh
```

This runs:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -vv
uv run mkdocs build --strict
```

## Helper scripts

| Script | Purpose |
| --- | --- |
| `scripts/check.sh` | Run the full local quality gate. |
| `scripts/format.sh` | Format code and apply safe Ruff fixes. |
| `scripts/test.sh` | Run pytest and forward extra pytest arguments. |
| `scripts/docs.sh serve` | Serve the documentation site locally. |
| `scripts/docs.sh build` | Build docs in strict mode. |
| `scripts/benchmark.sh` | Run benchmark scenarios. |

Examples:

```bash
scripts/test.sh tests/test_sql_sqlite.py -vv
scripts/docs.sh serve
scripts/benchmark.sh --iterations 10000
```

## Formatting and linting

```bash
scripts/format.sh
uv run ruff format --check .
uv run ruff check .
```

## Type checking

Paramora uses Pyright in strict mode for package code, tests, and benchmarks:

```bash
uv run pyright
```

## Tests

```bash
uv run pytest -vv
```

The suite includes unit tests, FastAPI integration tests, SQLite integration
tests, mongomock-backed Mongo tests, SQLAlchemy/SQLModel tests, and optional
PostgreSQL tests.

The PostgreSQL integration test requires:

```bash
export PARAMORA_POSTGRES_DSN='postgresql://user:password@localhost:5432/dbname'
uv run pytest -vv -m postgres
```

## Documentation

```bash
scripts/docs.sh serve
scripts/docs.sh build
```

Docs are built with MkDocs Material and deployed to GitHub Pages.

## Packaging policy

The wheel contains the runtime `paramora` package and type marker. The source
distribution includes tests, docs, examples, benchmarks, scripts, and contributor
files. Docs stay in the main branch so README, PyPI, and GitHub Pages links all
refer to the same source of truth.
