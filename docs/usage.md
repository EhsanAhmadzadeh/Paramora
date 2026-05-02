# Usage guide

This guide shows how to use Paramora in real FastAPI applications with both
MongoDB and SQL backends. It also explains strict mode, loose mode, contracts,
operators, sorting, pagination, aliases, required fields, and error handling.

## Mental model

Paramora follows this pipeline:

```text
HTTP query parameters
→ Query / QueryContract
→ parser and type coercion
→ backend-neutral QueryAst
→ emitter
→ backend-specific output
```

For MongoDB, the backend output is `MongoQuery`.

For SQL, the backend output is `SqlQuery`.

Your route handler receives:

```python
CompiledQuery[T]
```

where `T` is the backend output type.

```python
query.output  # MongoQuery, SqlQuery, or a custom emitter output
query.ast     # backend-neutral AST, useful for debugging and custom tooling
```

## Installation

```bash
uv add paramora
```

or:

```bash
pip install paramora
```

## Strict mode with MongoDB

Strict mode is the recommended mode for public APIs. It is enabled automatically
when you pass a `QueryContract` to `Query`.

```python
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI
from paramora import CompiledQuery, MongoQuery, Query, QueryContract, query_field

app = FastAPI()


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in", "nin")]
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

A request like this:

```http
GET /items?status__in=free,busy&active=true&price__gte=10&sort=-created_at&limit=20
```

emits a MongoDB query object similar to:

```python
MongoQuery(
    filter={
        "status": {"$in": ["free", "busy"]},
        "active": True,
        "price": {"$gte": 10.0},
    },
    sort=[("created_at", -1)],
    limit=20,
    offset=0,
)
```

Strict mode validates all of these decisions:

- `status` is declared
- `in` is allowed for `status`
- `active` is parsed as a boolean
- `price` is parsed as a float
- `created_at` is sortable
- `limit` is not larger than `max_limit`

If the request contains an unknown field, unsupported operator, invalid value,
or non-sortable field, Paramora returns a structured FastAPI `422` response.

## Strict mode with SQL

SQL support uses the same contract model. You only change the emitter.

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
    status: Annotated[str, query_field("eq", "in", "nin")]
    active: bool
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

For this request:

```http
GET /items?status__in=free,busy&active=true&price__lte=100&sort=-created_at
```

Paramora emits:

```python
SqlQuery(
    where='"status" IN (?, ?) AND "active" = ? AND "price" <= ?',
    params=("free", "busy", True, 100.0),
    order_by=('"created_at" DESC',),
    limit=20,
    offset=0,
)
```

`SqlQuery.where` is a fragment without the leading `WHERE`. `SqlQuery.order_by`
contains fragments without the leading `ORDER BY`. Your application composes the
final SQL statement.

## Loose mode with MongoDB

Loose mode is enabled when no contract is provided:

```python
from fastapi import Depends, FastAPI
from paramora import CompiledQuery, MongoQuery, Query

app = FastAPI()

loose_query: Query[MongoQuery] = Query(default_limit=20, max_limit=100)


@app.get("/admin/items")
def list_items(query: CompiledQuery[MongoQuery] = Depends(loose_query)):
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
GET /admin/items?status=free&price__gte=10&sort=-created_at
```

Because there is no contract, unknown fields are accepted. Values for unknown
fields remain strings, except list operators split comma-separated values:

```python
MongoQuery(
    filter={
        "status": "free",
        "price": {"$gte": "10"},
    },
    sort=[("created_at", -1)],
    limit=20,
    offset=0,
)
```

Loose mode is useful for internal tools, prototypes, and trusted admin APIs. It
is not recommended for public APIs because unknown field names and operators are
not checked against a contract.

Loose mode is still not raw backend passthrough. Paramora rejects raw backend
operator syntax such as:

```http
/items?$where=...
/items?price[$gte]=10
/items?price__$gte=10
```

## Loose mode with SQL

Loose SQL mode can be useful for internal dashboards, but use it carefully.
Unknown field names become SQL identifiers if they pass Paramora's identifier
safety checks.

```python
from paramora import CompiledQuery, Query, SqlEmitter, SqlQuery

loose_sql_query: Query[SqlQuery] = Query(
    emitter=SqlEmitter(param_style="qmark"),
    default_limit=50,
    max_limit=500,
)
```

Request:

```http
GET /admin/items?status=free&price__gte=10&sort=-created_at
```

Possible output:

```python
SqlQuery(
    where='"status" = ? AND "price" >= ?',
    params=("free", "10"),
    order_by=('"created_at" DESC',),
    limit=50,
    offset=0,
)
```

For public SQL-backed endpoints, prefer strict contracts. SQL identifiers cannot
be bound as parameters, so the safest API is one where every field that can
become a SQL identifier is declared by your application.

## Defining contract fields

A contract is a class that inherits from `QueryContract`.

```python
class ItemQuery(QueryContract):
    active: bool
```

Bare annotations accept only equality filters. This means `active=true` works,
but `active__ne=true` does not unless `ne` is explicitly allowed.

Use `Annotated` and `query_field(...)` for extra metadata:

```python
class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in", "nin")]
    price: Annotated[float, query_field("eq", "gt", "gte", "lt", "lte")]
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
```

### Required filters

Required fields are useful for multi-tenant APIs or endpoints that must always
receive a safety filter.

```python
class ItemQuery(QueryContract):
    tenant_id: Annotated[str, query_field(required=True)]
    status: Annotated[str, query_field("eq", "in")]
```

If `tenant_id` is missing, strict mode raises:

```json
{
  "detail": [
    {
      "loc": ["query", "tenant_id"],
      "msg": "Required filter field is missing.",
      "type": "query.required"
    }
  ]
}
```

### Backend aliases

Aliases let your public query parameter name differ from the backend field name.

MongoDB example:

```python
class ItemQuery(QueryContract):
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True, alias="createdAt"),
    ]
```

Request:

```http
GET /items?created_at__gte=2026-01-01T00:00:00Z&sort=-created_at
```

Mongo output uses `createdAt`:

```python
MongoQuery(
    filter={"createdAt": {"$gte": datetime(...)}},
    sort=[("createdAt", -1)],
    limit=50,
    offset=0,
)
```

SQL example:

```python
class ItemQuery(QueryContract):
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True, alias="items.created_at"),
    ]
```

SQL output uses a quoted identifier:

```sql
"items"."created_at" >= ?
```

## Supported types

Paramora currently supports these contract field types:

- `str`
- `int`
- `float`
- `bool`
- `datetime.datetime`
- simple `enum.Enum` subclasses

For `in` and `nin`, Paramora parses comma-separated lists and coerces each item
using the declared field type.

```python
from enum import Enum
from typing import Annotated


class Status(Enum):
    FREE = "free"
    BUSY = "busy"


class ItemQuery(QueryContract):
    status: Annotated[Status, query_field("eq", "in")]
```

Request:

```http
GET /items?status__in=free,busy
```

The emitted values are enum instances.

## Boolean parsing

Boolean parsing is case-insensitive. Accepted true values:

```text
true, 1, yes, on
```

Accepted false values:

```text
false, 0, no, off
```

Invalid values raise `query.type_error.bool`.

## Datetime parsing

Datetime fields use standard-library ISO-8601 parsing. A trailing `Z` is treated
as UTC.

```http
/items?created_at__gte=2026-01-01T12:30:00Z
```

Invalid values raise `query.type_error.datetime`.

## Sorting

Sorting uses the reserved `sort` query parameter.

```http
/items?sort=created_at
/items?sort=-created_at
```

In strict mode, the field must be declared as sortable:

```python
class ItemQuery(QueryContract):
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
```

Fields are not sortable by default. This is intentional because sorting can have
performance and indexing implications.

## Pagination

Paramora supports `limit` and `offset`:

```http
/items?limit=20&offset=40
```

The `Query` object controls defaults and maximums:

```python
item_query = Query(ItemQuery, default_limit=20, max_limit=100)
```

Rules:

- missing `limit` uses `default_limit`
- missing `offset` uses `0`
- `limit` must be an integer greater than or equal to zero
- `offset` must be an integer greater than or equal to zero
- `limit` cannot exceed `max_limit`

## Direct parsing outside FastAPI

`Query` can also be used directly in tests, scripts, and service layers.

```python
item_query: Query[MongoQuery] = Query(ItemQuery)
compiled = item_query.parse({
    "status__in": "free,busy",
    "price__gte": "10",
    "sort": "-created_at",
})

mongo = compiled.output
```

Direct parsing raises `QueryValidationError` instead of `HTTPException`:

```python
from paramora import QueryValidationError

try:
    item_query.parse({"price": "not-a-number"})
except QueryValidationError as exc:
    print(exc.to_list())
```

## Choosing MongoDB or SQL

Use the default emitter for MongoDB:

```python
item_query: Query[MongoQuery] = Query(ItemQuery)
```

Use `SqlEmitter` for SQL fragments:

```python
item_query: Query[SqlQuery] = Query(ItemQuery, emitter=SqlEmitter())
```

The route typing follows the configured backend output:

```python
def list_items(query: CompiledQuery[MongoQuery] = Depends(mongo_query)):
    mongo = query.output


def list_items_sql(query: CompiledQuery[SqlQuery] = Depends(sql_query)):
    sql = query.output
```

## Security guidance

For public APIs:

- prefer strict contracts
- explicitly allow only the operators you need
- make fields sortable only when there is an index or a clear product need
- use required tenant/user filters when appropriate
- keep raw MongoDB operators and raw SQL out of request syntax
- pass SQL values as bound parameters, never string-format them into SQL

Loose mode is helpful, but it should be used deliberately.
