# SQL backend

Paramora's SQL backend compiles the backend-neutral AST into parameterized SQL
fragments. It does not open a database connection, does not execute SQL, and does
not try to be an ORM.

Use SQL output when you want Paramora's query contracts, validation, and type
coercion, but your application owns the actual SQL execution layer.

## Output shape

`SqlEmitter` returns `SqlQuery`:

```python
SqlQuery(
    where='"price" >= ? AND "status" IN (?, ?)',
    params=(10.0, "free", "busy"),
    order_by=('"created_at" DESC',),
    limit=20,
    offset=0,
)
```

Fields:

- `where`: SQL predicate fragment without the leading `WHERE`
- `params`: bound values for placeholders in `where`
- `order_by`: SQL ordering fragments without the leading `ORDER BY`
- `limit`: validated limit integer
- `offset`: validated offset integer

## Why fragments instead of a full SELECT?

A complete SQL query is application-specific. Paramora should not decide:

- table names
- selected columns
- joins
- tenant filters
- authorization filters
- transactions
- connection lifetime
- driver or ORM integration

Paramora focuses on the part that comes from HTTP query parameters: filters,
sorting, limit, and offset.

## Complete FastAPI + SQLite-style example

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
    price: Annotated[float, query_field("eq", "gt", "gte", "lt", "lte")]


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

## Example request and output

Request:

```http
GET /items?status__in=free,busy&active=true&price__gte=10&sort=-created_at
```

Output:

```python
SqlQuery(
    where='"status" IN (?, ?) AND "active" = ? AND "price" >= ?',
    params=("free", "busy", True, 10.0),
    order_by=('"created_at" DESC',),
    limit=20,
    offset=0,
)
```

Final statement composition:

```python
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
```

## Parameter styles

Different DB-API drivers expect different placeholder styles. Configure the SQL
emitter with the style your driver expects.

```python
SqlEmitter(param_style="qmark")    # ?
SqlEmitter(param_style="format")   # %s
SqlEmitter(param_style="numeric")  # :1, :2
SqlEmitter(param_style="pyformat") # %(p1)s, %(p2)s
```

Examples:

```python
Query(ItemQuery, emitter=SqlEmitter(param_style="qmark"))
Query(ItemQuery, emitter=SqlEmitter(param_style="format"))
```

`SqlQuery.params` is always a tuple of values. If your driver expects a mapping
for `pyformat`, adapt it in your data access layer.

## Identifier safety

SQL values can be bound as parameters, but identifiers cannot. Column names must
therefore be controlled and validated before they are interpolated into SQL text.

Paramora validates identifiers and quotes them by default:

```python
SqlEmitter(quote_identifiers=True)
```

A contract alias such as:

```python
class ItemQuery(QueryContract):
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True, alias="items.created_at"),
    ]
```

emits:

```sql
"items"."created_at"
```

Unsafe identifiers raise `ValueError` during emission.

## Strict mode with SQL

Strict mode is recommended for public SQL-backed APIs.

```python
item_query: Query[SqlQuery] = Query(ItemQuery, emitter=SqlEmitter())
```

Strict mode means every SQL identifier came from your contract, not directly from
untrusted input. That is the safest way to expose filtering over SQL databases.

## Loose mode with SQL

Loose mode accepts unknown fields when there is no contract:

```python
loose_query: Query[SqlQuery] = Query(emitter=SqlEmitter())
```

Request:

```http
GET /items?status=free&price__gte=10&sort=-created_at
```

Output:

```python
SqlQuery(
    where='"status" = ? AND "price" >= ?',
    params=("free", "10"),
    order_by=('"created_at" DESC',),
    limit=50,
    offset=0,
)
```

Unknown values remain strings. Unknown identifiers must still pass Paramora's
identifier validation.

Loose SQL mode is best reserved for trusted internal tools. For public APIs,
prefer strict contracts.

## Injection resistance

Paramora never interpolates user values into SQL text.

Request:

```http
GET /items?status=free'%20OR%201=1%20--
```

Output:

```python
SqlQuery(
    where='"status" = ?',
    params=("free' OR 1=1 --",),
    order_by=(),
    limit=50,
    offset=0,
)
```

The payload is data, not executable SQL, as long as you pass `params` to your
driver as bound parameters.

Do this:

```python
connection.execute(statement, (*sql.params, sql.limit, sql.offset))
```

Do not do this:

```python
# Wrong: never string-format user values into SQL.
statement = f"SELECT * FROM items WHERE status = '{user_status}'"
```

## Operators

The SQL backend supports the same core operators as MongoDB:

| Paramora operator | SQL output |
| --- | --- |
| `eq` | `=` |
| `ne` | `!=` |
| `gt` | `>` |
| `gte` | `>=` |
| `lt` | `<` |
| `lte` | `<=` |
| `in` | `IN (...)` |
| `nin` | `NOT IN (...)` |

## Current scope

The SQL backend is intentionally conservative. It does not currently support:

- joins
- boolean groups such as nested `OR`
- aggregations
- raw SQL snippets
- full-text search
- SQLAlchemy expression objects
- database-specific operators

Future versions may add SQLAlchemy or driver-specific emitters after the AST,
error model, and extension API stabilize further.

## Testing SQL behavior

Paramora includes two SQL test layers:

1. emitter tests that assert exact `SqlQuery` output
2. SQLite integration tests that execute emitted fragments against an in-memory
   database

Run SQL tests with:

```bash
uv run pytest -vv tests/test_sql_emitter.py tests/test_sql_sqlite.py
```
