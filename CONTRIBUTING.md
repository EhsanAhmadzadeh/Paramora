# Contributing

Paramora is an early-stage open-source Python package. Contributions should keep
the API small, typed, documented, and FastAPI-native.

## Local setup

Paramora is developed uv-first:

```bash
uv sync --group dev
```

## Quality checks

Run these before opening a pull request:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -vv
```

## Testing style

Tests use pytest and should follow Arrange/Act/Assert:

```python
from typing import Annotated


def test_example() -> None:
    # Arrange
    class MyContract(QueryContract):
        status: Annotated[str, query_field("eq", "in")]

    query = Query(MyContract)

    # Act
    mongo = query.parse({"status": "free"}).to_mongo()

    # Assert
    assert mongo.filter == {"status": "free"}
```

Prefer focused tests that verify one behavior. Use `mongomock` when the behavior
should be proven against a Mongo-like collection, not just a dictionary shape.

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
- Prefer one clear public API over duplicate convenience APIs.
- Avoid adding new public APIs until the use case is clear.

## Coverage expectations

New parser, coercion, contract, and emitter behavior should include focused unit
tests. Behavior that claims Mongo compatibility should include a `mongomock`
integration test when practical.

The test command runs coverage by default. Do not chase artificial 100% coverage
at the expense of useful tests, but newly added behavior should be covered.

## Profiling changes

Performance work should include before/after evidence. Start with:

```bash
uv run python benchmarks/profile_parse.py
```

Include profiler output or a concise summary in performance-focused pull
requests.
