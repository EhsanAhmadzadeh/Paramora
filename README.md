# Paramora

Paramora is safe typed query compilation for FastAPI. It turns HTTP query
parameters into a backend-neutral AST, then emits backend-specific query objects.
The current MVP is FastAPI-native and currently supports MongoDB output.

> Status: 0.1 pre-release. The API is still allowed to change before the first
> stable release.

## Documentation

The README gives the short path. The full user and contributor documentation is
kept in this repository under [`docs/`](docs/):


- [Quickstart](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/quickstart.md)
- [Query contracts](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/contracts.md)
- [Query syntax](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/query-syntax.md)
- [Error handling](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/errors.md)
- [MongoDB backend](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/mongodb.md)
- [Development with uv](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/development.md)
- [Testing strategy](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/testing.md)
- [Profiling and future Rust hotspots](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/profiling-and-rust.md)


Docs live on the main branch so GitHub, source distributions, and PyPI readers
can find the same authoritative material. Wheels only need the runtime
`paramora` package.

## Installation

Paramora is designed for FastAPI applications. The package is not published yet;
when it is, installation will look like this:

```bash
uv add paramora
```

For local development from the repository:

```bash
uv sync --group dev
```

## Quickstart

Define a type-checker-friendly query contract with `typing.Annotated`, pass it to
`Query`, and mount it with FastAPI using `Depends(item_query)`.

```python
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI
from paramora import CompiledQuery, Query, QueryContract, query_field

app = FastAPI()


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in")]
    active: bool
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True),
    ]
    price: Annotated[float, query_field("eq", "gt", "gte", "lt", "lte")]


item_query = Query(ItemQuery, default_limit=20, max_limit=100)


@app.get("/items")
def list_items(query: CompiledQuery = Depends(item_query)):
    mongo = query.to_mongo()
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

Mongo output:

```python
MongoQuery(
    filter={"status": {"$in": ["free", "busy"]}, "active": True},
    sort=[("created_at", -1)],
    limit=20,
    offset=0,
)
```

## Modes

Paramora has one simple mode rule:

- `Query()` has no contract and defaults to loose mode.
- `Query(MyContract)` has a contract and defaults to strict mode.

Strict mode is recommended for public endpoints. Loose mode is useful for
prototypes and trusted internal tools.

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
better autocomplete for `query_field("eq", "in")` than for a nested tuple such as
`allow=("eq", "in")`.

## MongoDB backend

MongoDB is the first supported backend. Paramora currently emits Mongo filter
dictionaries, PyMongo-compatible sort pairs, `limit`, and `offset`.

```python
mongo = query.to_mongo()
collection.find(mongo.filter).sort(mongo.sort).skip(mongo.offset).limit(mongo.limit)
```

Other backends are planned after the public contract, AST, and error model are
stable.

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

See [Error handling](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/errors.md) for stable error-code semantics.

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
Mongo-like execution tests use `mongomock`; parser and coercion behavior are
covered by focused unit tests.
