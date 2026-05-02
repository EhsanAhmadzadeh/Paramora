# Paramora

Paramora is **safe typed query compilation for FastAPI**.

It turns user-controlled HTTP query parameters into a small backend-neutral AST,
then emits backend query objects such as MongoDB query dictionaries or
parameterized SQL fragments.

Paramora is designed for teams that want query filtering to be explicit,
validated, typed, documented, and safe by default.

> Status: alpha. Public APIs, AST shapes, error codes, and emitter contracts may
> change before `1.0`.

## Why Paramora?

FastAPI makes request handling ergonomic, but filtering APIs often end up with
one of two unsafe or messy patterns:

1. manually parsing query parameters in every route
2. exposing backend-specific query syntax directly to clients

Paramora gives you a middle path:

- clients send simple query parameters such as `price__gte=10`
- your application declares which fields and operators are allowed
- Paramora validates and coerces values into Python types
- Paramora builds a backend-neutral AST
- an emitter produces a backend-specific output, currently MongoDB or SQL

Request clients never need to know raw MongoDB operators or SQL fragments.

## Installation

With uv:

```bash
uv add paramora
```

With pip:

```bash
pip install paramora
```

For local development from the repository:

```bash
uv sync --group dev
```

## Requirements

Paramora supports **Python 3.10+** and FastAPI `0.115+`.

Python 3.10 is the compatibility baseline. Runtime code intentionally avoids
Python 3.11+/3.12+ only syntax so users on Python 3.10 and 3.11 can install the
package. The minimum supported Python version may be raised in future releases
after older versions reach end-of-life.

## The core API

Most applications use these objects:

```python
from paramora import CompiledQuery, Query, QueryContract, query_field
```

Backend-specific outputs:

```python
from paramora import MongoQuery, SqlEmitter, SqlQuery
```

The important rule is:

- `Query()` has no contract and defaults to **loose mode**.
- `Query(MyContract)` has a contract and defaults to **strict mode**.

Strict mode is recommended for public APIs. Loose mode is useful for prototypes,
trusted internal tools, and admin utilities.

## MongoDB quickstart

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

    docs = (
        collection
        .find(mongo.filter)
        .sort(mongo.sort)
        .skip(mongo.offset)
        .limit(mongo.limit)
    )

    return list(docs)
```

Request:

```http
GET /items?status__in=free,busy&active=true&sort=-created_at&limit=20
```

Emitted output:

```python
MongoQuery(
    filter={"status": {"$in": ["free", "busy"]}, "active": True},
    sort=[("created_at", -1)],
    limit=20,
    offset=0,
)
```

## SQL quickstart

Paramora's SQL backend emits **parameterized fragments**, not a complete SQL
statement. Your application still owns table names, selected columns,
connections, transactions, joins, and authorization filters.

```python
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI
from paramora import (
    CompiledQuery,
    Query,
    QueryContract,
    SqlEmitter,
    SqlQuery,
    query_field,
)

app = FastAPI()


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in")]
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
    price: Annotated[float, query_field("eq", "gte", "lte")]


item_query: Query[SqlQuery] = Query(
    ItemQuery,
    emitter=SqlEmitter(param_style="qmark"),
    default_limit=20,
    max_limit=100,
)


@app.get("/items")
def list_items(query: CompiledQuery[SqlQuery] = Depends(item_query)):
    sql = query.output

    where_clause = f" WHERE {sql.where}" if sql.where else ""
    order_clause = f" ORDER BY {', '.join(sql.order_by)}" if sql.order_by else ""

    statement = f"""
    SELECT id, status, created_at, price
    FROM items
    {where_clause}
    {order_clause}
    LIMIT ? OFFSET ?
    """

    rows = connection.execute(
        statement,
        (*sql.params, sql.limit, sql.offset),
    ).fetchall()

    return [dict(row) for row in rows]
```

Request:

```http
GET /items?status__in=free,busy&price__gte=10&sort=-created_at
```

Emitted SQL output:

```python
SqlQuery(
    where='"status" IN (?, ?) AND "price" >= ?',
    params=("free", "busy", 10.0),
    order_by=('"created_at" DESC',),
    limit=20,
    offset=0,
)
```

Values are returned separately in `params`; they should be passed to your driver
as bound parameters. Do not format user values into SQL strings.

## Query contracts

Bare annotations allow equality filtering:

```python
class ItemQuery(QueryContract):
    active: bool
```

This accepts:

```http
/items?active=true
```

Use `typing.Annotated` with `query_field(...)` for extra operators, sorting,
backend aliases, or required filters:

```python
class ItemQuery(QueryContract):
    tenant_id: Annotated[str, query_field(required=True)]
    status: Annotated[str, query_field("eq", "in", "nin")]
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True, alias="createdAt"),
    ]
```

The positional operator API is deliberate. Editors such as Pylance can provide
better autocomplete for `query_field("eq", "in")` than for nested tuple APIs.

## Query syntax

Paramora uses Django-style operator suffixes:

| Query parameter | Meaning |
| --- | --- |
| `status=free` | `status == "free"` |
| `status__in=free,busy` | `status in ["free", "busy"]` |
| `price__gte=10` | `price >= 10` |
| `price__lt=20` | `price < 20` |
| `sort=created_at` | sort ascending |
| `sort=-created_at` | sort descending |
| `limit=20` | return at most 20 rows/documents |
| `offset=40` | skip 40 rows/documents |

Supported operators today:

```text
eq, ne, gt, gte, lt, lte, in, nin
```

## Strict mode and loose mode

### Strict mode

`Query(MyContract)` validates requests against the declared contract:

- unknown fields are rejected
- unsupported operators are rejected
- declared field types are used for coercion
- sorting is allowed only on declared sortable fields
- required filters are enforced
- raw backend operator syntax is rejected

Use strict mode for public endpoints.

### Loose mode

`Query()` has no contract. Unknown fields are allowed and values are kept as
strings unless list syntax is used with `in` or `nin`.

```python
loose_query: Query[MongoQuery] = Query(default_limit=20, max_limit=100)


@app.get("/admin/items")
def list_items(query: CompiledQuery[MongoQuery] = Depends(loose_query)):
    return list(collection.find(query.output.filter))
```

Loose mode still rejects raw backend operator syntax such as `$where`,
`price[$gte]`, and `price__$gte`. It is less schema-strict, not raw database
passthrough.

## Error handling

Invalid query parameters produce structured FastAPI-compatible errors:

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

The same validation model is used by direct `Query.parse(...)` calls and FastAPI
request dependencies.

## Documentation

The README is the short introduction. Full documentation lives in `docs/`:

- [Documentation index](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/README.md)
- [Usage guide](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/usage.md)
- [Quickstart](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/quickstart.md)
- [Query contracts](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/contracts.md)
- [Query syntax](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/query-syntax.md)
- [MongoDB backend](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/mongodb.md)
- [SQL backend](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/sql.md)
- [Error handling](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/errors.md)
- [Python support policy](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/python-support.md)
- [Development with uv](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/development.md)
- [Testing strategy](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/testing.md)
- [Benchmarking, profiling, and future Rust hotspots](https://github.com/EhsanAhmadzadeh/Paramora/blob/main/docs/profiling-and-rust.md)

Docs live on the main branch. Wheels include only the runtime `paramora` package;
source distributions can include docs for maintainers and contributors.

## Development

This repository is uv-first:

```bash
uv sync --group dev
uv run pytest -vv
uv run ruff format --check .
uv run ruff check .
uv run pyright
```

The test suite includes focused parser/coercion tests, FastAPI dependency tests,
MongoDB-style tests with `mongomock`, and SQLite integration tests for emitted
SQL fragments.
