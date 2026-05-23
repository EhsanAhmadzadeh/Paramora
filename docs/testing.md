# Testing strategy

Paramora aims to be reliable enough for production FastAPI APIs, so tests cover
behavior at several layers. The suite is written with pytest and follows the AAA
pattern: Arrange, Act, Assert.

## Test layers

| Layer | Purpose |
| --- | --- |
| Contract tests | Validate `QueryContract`, `Annotated`, and `query_field(...)` behavior |
| Coercion tests | Validate scalar, enum, boolean, datetime, and list coercion |
| Parser tests | Validate strict mode, loose mode, operators, sorting, pagination, and errors |
| FastAPI tests | Validate dependency behavior and HTTP 422 responses |
| Mongo tests | Execute emitted Mongo queries against `mongomock` |
| Raw SQL tests | Execute emitted SQL against in-memory SQLite |
| PostgreSQL SQL-shape tests | Validate PostgreSQL placeholder styles and injection safety |
| SQLAlchemy tests | Validate table, model, and mapping column resolution |
| SQLModel tests | Validate SQLModel class integration with SQLAlchemy-compatible emitters |
| ODM tests | Validate Beanie/MongoEngine-friendly output helpers |

## Run the full normal suite

```bash
uv sync --group dev
uv run pytest -vv
```

The `dev` dependency group installs the optional backend libraries needed for the
normal backend suite, including `mongomock`, `sqlalchemy`, `sqlmodel`, `beanie`,
and `mongoengine`.

## PostgreSQL integration tests

PostgreSQL execution tests require a real database. They are skipped unless
`PARAMORA_POSTGRES_DSN` is set.

```bash
PARAMORA_POSTGRES_DSN="postgresql://user:pass@localhost:5432/paramora_test" \
  uv run pytest -vv -m postgres
```

## Marker examples

Run only MongoDB-compatible tests:

```bash
uv run pytest -vv -m mongo
```

Run only SQL tests:

```bash
uv run pytest -vv -m sql
```

Run SQLAlchemy and SQLModel tests:

```bash
uv run pytest -vv -m sqlalchemy
```

## Type safety in tests

Paramora keeps tests under Pyright strict mode. Tests should avoid leaking
`Unknown` types from optional third-party libraries into assertions. Use small
local protocols, typed helper functions, or `Any` only at the boundary where a
third-party dynamic object is intentionally imported.

## Coverage

Coverage is a signal, not the goal. Paramora requires meaningful behavioral
coverage around safety-critical paths: validation, query syntax, emitter output,
and backend execution behavior.
