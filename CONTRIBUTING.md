# Contributing

Paramora is an early-stage open-source Python package. Contributions should keep
the API small, typed, documented, reliable, and FastAPI-native.

## Local setup

Paramora is developed uv-first:

```bash
uv sync --group dev --group docs
```

The development environment installs optional backend libraries used by the test
suite, including `mongomock`, SQLAlchemy, SQLModel, psycopg, Beanie, and
MongoEngine.

## Quality checks

Run the local quality gate before opening a pull request:

```bash
scripts/check.sh
```

That command runs formatting checks, linting, Pyright strict type checking,
pytest, and a strict MkDocs build.

Useful focused commands:

```bash
scripts/format.sh
scripts/test.sh tests/test_sql_sqlite.py -vv
scripts/docs.sh serve
scripts/benchmark.sh
```

## Testing style

Tests use pytest and should follow Arrange/Act/Assert:

```python
from typing import Annotated

from paramora import MongoQuery, Query, QueryContract, query_field


def test_example() -> None:
    # Arrange
    class MyContract(QueryContract):
        status: Annotated[str, query_field("eq", "in")]

    query: Query[MongoQuery] = Query(MyContract)

    # Act
    mongo = query.parse({"status": "free"}).output

    # Assert
    assert mongo.filter == {"status": "free"}
```

Prefer focused tests that verify one behavior. Use parametrization for repeated
syntax or coercion cases. Use `mongomock` when Mongo behavior should be proven
against a Mongo-like collection, not just a dictionary shape. Use SQLite for raw
SQL execution tests because it is available in the Python standard library.

## Contract typing style

Use `typing.Annotated` for Paramora metadata:

```python
status: Annotated[str, query_field("eq", "in")]
```

Do not assign `query_field(...)` to an annotated class attribute:

```python
status: str = query_field("eq", "in")
```

The assignment style makes type checkers report that `QueryFieldInfo` is not
assignable to `str`, `datetime`, or the declared field type.

## API design principles

- FastAPI ergonomics come first.
- No contract means loose mode.
- A contract means strict mode.
- Query params compile to a backend-neutral AST before emission.
- Do not expose raw backend operators in HTTP query syntax.
- Values must be bound parameters for SQL outputs, never interpolated strings.
- Prefer one clear public API over duplicate convenience APIs.
- Avoid adding new public APIs until the use case is clear.

## Documentation expectations

Update docs whenever public behavior changes. Most user-facing changes should
update at least one of:

- `README.md`
- `docs/usage.md`
- `docs/how-to.md`
- backend-specific docs under `docs/`

Build docs locally with:

```bash
scripts/docs.sh build
```

## Coverage expectations

New parser, coercion, contract, and emitter behavior should include focused unit
or integration tests. Behavior that claims compatibility with a backend should
include backend-level tests where practical.

The test command runs coverage by default. Do not chase artificial 100% coverage
at the expense of useful tests, but newly added behavior should be covered.

## Profiling changes

Performance work should include before/after evidence. Start with:

```bash
uv run python benchmarks/profile_parse.py
scripts/benchmark.sh
```

Include profiler output or a concise summary in performance-focused pull
requests.
