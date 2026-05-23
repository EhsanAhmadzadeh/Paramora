# Testing strategy

Paramora aims to be reliable enough for public FastAPI APIs, so tests cover more
than dictionary-shape assertions.

## Test layers

- **Unit tests** validate parsing, coercion, contracts, errors, and emitters.
- **FastAPI integration tests** verify dependency behavior and `422` responses.
- **Mongo integration tests** execute generated Mongo queries against
  `mongomock`.
- **SQLite integration tests** execute generated SQL with the standard-library
  `sqlite3` module.
- **PostgreSQL tests** validate PostgreSQL-compatible SQL output and optionally
  execute against a real PostgreSQL database.
- **SQLAlchemy / SQLModel tests** verify expression emission and statement
  application.
- **ODM tests** verify adapter helper output for common ODM usage patterns.

## Run all tests

```bash
uv sync --group dev --group docs
uv run pytest -vv
```

or through the helper script:

```bash
scripts/test.sh
```

## Test style

Tests should follow the AAA pattern:

```python
def test_example_behavior() -> None:
    # Arrange
    query = Query(ItemQuery)

    # Act
    compiled = query.parse({"price__gte": "10"})

    # Assert
    assert compiled.output.filter == {"price": {"$gte": 10.0}}
```

Keep tests focused on one behavior, use parametrization for repeated cases, and
prefer integration tests when an emitter claims compatibility with a backend.

## Coverage

Coverage is enforced by pytest configuration and uploaded to Codecov from CI.
The README coverage badge is dynamic and reflects the latest coverage uploaded
for the `main` branch.
