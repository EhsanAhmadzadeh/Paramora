# Development with uv

Paramora is developed uv-first. The development environment intentionally
installs optional backend libraries so contributors can run the same high-value
suite across MongoDB-compatible behavior, raw SQL, SQLAlchemy, SQLModel, and ODM
adapters.

## Install dependencies

```bash
uv sync --group dev --group docs
```

The `dev` group includes:

- pytest and pytest-cov
- Ruff
- Pyright
- HTTPX and FastAPI test dependencies
- mongomock for MongoDB-compatible integration tests
- SQLAlchemy and SQLModel for expression-emitter tests
- psycopg for optional PostgreSQL integration tests
- Beanie and MongoEngine for ODM adapter import compatibility

The `docs` group includes MkDocs and Material for MkDocs.

## Run the quality gate

Before opening a pull request, run:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -vv
uv run mkdocs build --strict
```

## Run tests

```bash
uv run pytest -vv
```

PostgreSQL execution tests require a real database and are gated by
`PARAMORA_POSTGRES_DSN`:

```bash
PARAMORA_POSTGRES_DSN="postgresql://user:pass@localhost:5432/paramora_test" \
  uv run pytest -vv -m postgres
```

## Build docs locally

```bash
uv run mkdocs serve
```

Then open the local URL printed by MkDocs.

For the production build check:

```bash
uv run mkdocs build --strict
```

## Packaging policy

The wheel contains the runtime `paramora` package and the `py.typed` marker. The
source distribution includes tests, docs, examples, benchmarks, changelog, and
contributor files.
