# SQL backend

Paramora's SQL backend is an initial emitter that compiles the backend-neutral
AST into parameterized SQL fragments. It is not a full ORM, does not open a
database connection, and does not execute SQL for you.

The SQL backend is useful when you want Paramora's query-contract validation and
type coercion, but your application already owns the actual SQL execution layer.
That execution layer may be direct DB-API, SQLAlchemy Core, an internal query
service, or a repository class.

## Output shape

The SQL emitter returns a `SqlQuery` object:

```python
SqlQuery(
    where='"price" >= ? AND "status" IN (?, ?)',
    params=(10.0, "free", "busy"),
    order_by=('"created_at" DESC',),
    limit=20,
    offset=0,
)
```

`where` does not include the leading `WHERE` keyword. `order_by` does not include
the leading `ORDER BY` keyword. This keeps the output composable in applications
that control table names, joins, selected columns, transactions, and driver
behavior.

## Why fragments instead of a complete SELECT?

A complete SQL query requires application-specific decisions:

- table names
- selected columns
- joins
- tenant filters and authorization filters
- transactions
- connection libraries
- SQLAlchemy vs raw DB-API vs custom data layers

Paramora focuses on the query-parameter part: filters, sorting, limit, and
offset. You can then compose those fragments into your own data access layer.

## Usage

```python
from datetime import datetime
from typing import Annotated

from paramora import Query, QueryContract, SqlEmitter, SqlQuery, query_field


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in")]
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
    price: Annotated[float, query_field("eq", "gte", "lte")]


item_query: Query[SqlQuery] = Query(ItemQuery, emitter=SqlEmitter())
compiled = item_query.parse({
    "status__in": "free,busy",
    "price__gte": "10",
    "sort": "-created_at",
})

sql = compiled.output
```

## Executing with DB-API

Here is a minimal SQLite example. The same composition pattern works with other
DB-API drivers after choosing the right placeholder style.

```python
where_clause = f" WHERE {sql.where}" if sql.where else ""
order_clause = f" ORDER BY {', '.join(sql.order_by)}" if sql.order_by else ""

statement = f"""
SELECT id, status, price
FROM items
{where_clause}
{order_clause}
LIMIT ? OFFSET ?
"""

rows = connection.execute(
    statement,
    (*sql.params, sql.limit, sql.offset),
).fetchall()
```

`SqlQuery.params` contains only filter values. The example also binds `limit` and
`offset` as SQL parameters when executing the final statement. Paramora already
validates them as integers and enforces the configured maximum limit.

## Parameter styles

`SqlEmitter` supports common placeholder styles:

```python
SqlEmitter(param_style="qmark")    # ?
SqlEmitter(param_style="format")   # %s
SqlEmitter(param_style="numeric")  # :1, :2
SqlEmitter(param_style="pyformat") # %(p1)s, %(p2)s
```

Use the style expected by your driver. For example, SQLite uses `qmark`, while
some PostgreSQL/MySQL drivers use `format` or `pyformat` conventions.

Values are always returned separately in `SqlQuery.params`. Do not manually
format user values into SQL strings.

## Identifier safety

SQL values can be parameterized, but SQL identifiers cannot. Column names must
therefore be controlled by your application and validated before they are
interpolated into SQL text.

Paramora validates identifiers and double-quotes them by default:

```python
class ItemQuery(QueryContract):
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True, alias="items.created_at"),
    ]
```

This emits identifiers like:

```sql
"items"."created_at"
```

Loose mode can emit SQL for unknown fields, but identifiers still need to match a
safe identifier pattern. For public SQL-backed endpoints, prefer strict
contracts. Strict contracts let you explicitly decide which fields can become SQL
identifiers.

## Injection resistance

Paramora's SQL emitter never interpolates user values into the SQL text. This
query parameter:

```http
/items?status=free'%20OR%201=1%20--
```

is emitted as data:

```python
SqlQuery(
    where='"status" = ?',
    params=("free' OR 1=1 --",),
    ...
)
```

The database driver receives the payload as a bound value, not executable SQL.
The test suite includes SQLite integration coverage for this behavior.

## Testing

The SQL backend has two test layers:

1. emitter unit tests that assert exact `SqlQuery` output
2. SQLite integration tests that execute emitted fragments against an in-memory
   database

The SQLite tests cover equality, `in`, `nin`, `ne`, numeric ranges, booleans,
sorting, pagination, combined filters, loose-mode safe identifiers, and injection
payloads treated as data.

Run them with:

```bash
uv run pytest -vv tests/test_sql_emitter.py tests/test_sql_sqlite.py
```

## Current scope

The SQL backend currently covers the same core operators as MongoDB: `eq`, `ne`,
`gt`, `gte`, `lt`, `lte`, `in`, and `nin`.

It intentionally does not support joins, nested boolean groups, aggregations,
raw SQL snippets, full-text search, or SQLAlchemy expression objects yet. Future
versions may add SQLAlchemy-specific outputs after the contract, AST, and error
APIs settle further.
