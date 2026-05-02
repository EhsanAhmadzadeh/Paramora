# Quickstart

This guide shows the smallest useful Paramora setup for FastAPI. It includes a
MongoDB example, a SQL example, and the difference between strict and loose mode.

## Install

```bash
uv add paramora
```

or:

```bash
pip install paramora
```

## Step 1: define a query contract

A `QueryContract` declares which query fields your endpoint accepts. Use normal
Python annotations for types. Use `Annotated[..., query_field(...)]` when a field
needs extra operators, sorting, aliases, or required behavior.

```python
from datetime import datetime
from typing import Annotated

from paramora import QueryContract, query_field


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in")]
    active: bool
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
    price: Annotated[float, query_field("eq", "gt", "gte", "lt", "lte")]
```

This contract allows these query parameters:

```http
/items?status=free
/items?status__in=free,busy
/items?active=true
/items?created_at__gte=2026-01-01T00:00:00Z
/items?price__gte=10&price__lt=100
/items?sort=-created_at
```

## Step 2A: use it with MongoDB

When no emitter is provided, `Query` emits `MongoQuery`.

```python
from fastapi import Depends, FastAPI
from paramora import CompiledQuery, MongoQuery, Query

app = FastAPI()

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
GET /items?status__in=free,busy&active=true&sort=-created_at&limit=20
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

## Step 2B: use it with SQL

For SQL, configure `SqlEmitter`. Paramora emits parameterized SQL fragments.

```python
from fastapi import Depends, FastAPI
from paramora import CompiledQuery, Query, SqlEmitter, SqlQuery

app = FastAPI()

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
    SELECT id, status, active, created_at, price
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

SQL output:

```python
SqlQuery(
    where='"status" IN (?, ?) AND "price" >= ?',
    params=("free", "busy", 10.0),
    order_by=('"created_at" DESC',),
    limit=20,
    offset=0,
)
```

## Strict mode

Passing a contract enables strict mode by default:

```python
item_query = Query(ItemQuery)
```

Strict mode rejects:

- unknown fields
- unknown operators
- operators not allowed by the field
- sorting by fields that are not marked `sortable=True`
- invalid type values
- missing required filters
- raw backend operator syntax

Strict mode is the recommended mode for public APIs.

## Loose mode

Calling `Query()` without a contract enables loose mode:

```python
loose_query: Query[MongoQuery] = Query(default_limit=20, max_limit=100)
```

Loose mode accepts unknown fields and known Paramora operators:

```http
GET /items?status=free&price__gte=10&sort=-created_at
```

In loose mode, undeclared values remain strings:

```python
MongoQuery(
    filter={"status": "free", "price": {"$gte": "10"}},
    sort=[("created_at", -1)],
    limit=20,
    offset=0,
)
```

Loose mode is useful for prototypes and trusted internal tools. It is not raw
backend passthrough: `$where`, `price[$gte]`, and `price__$gte` are still
rejected.

## Next steps

- Read the full [usage guide](usage.md).
- Learn about [query contracts](contracts.md).
- Review the complete [query syntax](query-syntax.md).
- Use [MongoDB backend](mongodb.md) or [SQL backend](sql.md) docs for backend-specific details.
