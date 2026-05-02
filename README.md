# Paramora

Paramora is safe typed query compilation for FastAPI. It turns user-controlled
HTTP query parameters into a small backend-neutral AST, then emits backend query
objects such as MongoDB query dictionaries or parameterized SQL fragments.

The package is designed for FastAPI first, uses Python type annotations for query
contracts, and keeps raw backend operators out of request syntax.

> Status: alpha. Public APIs, AST shapes, error codes, and emitter contracts may
> change before `1.0`.

## Documentation

The README is the short introduction. Full documentation lives in `docs/` and is
linked here so GitHub and PyPI readers can find the same material:

- [Quickstart](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/quickstart.md)
- [Query contracts](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/contracts.md)
- [Query syntax](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/query-syntax.md)
- [Error handling](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/errors.md)
- [MongoDB backend](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/mongodb.md)
- [SQL backend](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/sql.md)
- [Python support policy](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/python-support.md)
- [Development with uv](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/development.md)
- [Testing strategy](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/testing.md)
- [Profiling and future hotspots](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/profiling-and-rust.md)

Docs live on the main branch. Wheels include only the runtime `paramora` package;
source distributions can include docs for maintainers and contributors.

## Installation

Paramora is uv-friendly:

```bash
uv add paramora
```

pip also works:

```bash
pip install paramora
```

For local development:

```bash
uv sync --group dev
```

## Requirements

Paramora supports Python `3.10+` and FastAPI `0.115+`.

The project targets Python 3.10 as the compatibility baseline. Newer Python
versions are supported through CI and tooling, but runtime code must remain valid
on Python 3.10. The minimum supported Python version may be raised in future
major or minor releases after older versions reach end-of-life and the ecosystem
moves forward. Any such change should be documented in the changelog and release
notes.

The code intentionally avoids Python 3.12+ only syntax such as PEP 695 `type`
alias declarations and new generic function syntax, so users on 3.10 and 3.11
can install the package.

## Quickstart with MongoDB

Define a query contract with `typing.Annotated`, pass it to `Query`, and mount it
as a FastAPI dependency.

```python
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI
from paramora import CompiledQuery, MongoQuery, Query, QueryContract, query_field

app = FastAPI()


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in")]
    active: bool
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True),
    ]
    price: Annotated[float, query_field("eq", "gt", "gte", "lt", "lte")]


item_query: Query[MongoQuery] = Query(ItemQuery, default_limit=20, max_limit=100)


@app.get("/items")
def list_items(query: CompiledQuery[MongoQuery] = Depends(item_query)):
    mongo = query.output

    return list(
        collection
        .find(mongo.filter)
        .sort(mongo.sort)
        .skip(mongo.offset)
        .limit(mongo.limit)
    )
```

Request:

```http
/items?status__in=free,busy&active=true&sort=-created_at&limit=20
```

Compiled output:

```python
MongoQuery(
    filter={"status": {"$in": ["free", "busy"]}, "active": True},
    sort=[("created_at", -1)],
    limit=20,
    offset=0,
)
```

## SQL backend preview

Paramora now ships an initial SQL emitter. It returns parameterized SQL fragments
instead of complete SQL strings. Values are returned separately in `params`.

```python
from paramora import Query, SqlEmitter, SqlQuery

item_query: Query[SqlQuery] = Query(ItemQuery, emitter=SqlEmitter())
compiled = item_query.parse({"price__gte": "10", "status__in": "free,busy"})
sql = compiled.output

assert sql.where == '"price" >= ? AND "status" IN (?, ?)'
assert sql.params == (10.0, "free", "busy")
```

The SQL backend is intentionally conservative. It validates identifiers, quotes
columns by default, and never interpolates user values into SQL text. The test
suite includes SQLite integration tests that execute emitted SQL fragments
against an in-memory database. It is a foundation for future SQLAlchemy and
driver-specific integrations.

## Modes

Paramora has one mode rule:

- `Query()` has no contract and defaults to loose mode.
- `Query(MyContract)` has a contract and defaults to strict mode.

Strict mode is recommended for public endpoints. Loose mode is useful for trusted
internal tools and prototypes. Loose mode still rejects raw backend operator
syntax such as `$where` or `price__$gte`.

## Contract fields

Bare annotations create equality-only filters:

```python
class ItemQuery(QueryContract):
    active: bool
```

Use `query_field(...)` inside `Annotated` for operators, sortability, aliases,
and required filters:

```python
class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in", "nin")]
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True, alias="createdAt"),
    ]
```

The positional operator API is deliberate: editors such as Pylance can provide
better autocomplete for `query_field("eq", "in")` than for nested tuple APIs.

## Backend output and generics

`Query` is generic over the backend output type:

```python
mongo_query: Query[MongoQuery] = Query(ItemQuery)
sql_query: Query[SqlQuery] = Query(ItemQuery, emitter=SqlEmitter())
```

`CompiledQuery[T].output` has the selected backend type. This avoids redundant
APIs such as `to(...)` and `to_mongo()` and keeps the hot path simple: parsing
produces an AST once, then the configured emitter produces one backend output.

## Error handling

Validation errors are structured and FastAPI-compatible:

```json
{
  "detail": [
    {
      "loc": ["query", "price"],
      "msg": "Expected a float-compatible value.",
      "type": "query.type_error.float",
      "input": "bad"
    }
  ]
}
```

See [Error handling](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/errors.md)
for stable error-code semantics.

## Development

This repository is uv-first:

```bash
uv sync --group dev
uv run pytest -vv
uv run ruff format --check .
uv run ruff check .
uv run pyright
```

The default pytest configuration runs coverage with missing-line reporting.
Mongo-like execution tests use `mongomock`; SQL execution tests use in-memory
SQLite from the Python standard library; parser and coercion behavior are
covered by focused unit tests.
