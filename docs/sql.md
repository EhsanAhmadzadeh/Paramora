# Raw SQL backend

Paramora's SQL backend emits **parameterized raw SQL fragments**. It is not an
ORM and it does not open database connections. The application remains
responsible for table ownership, selected columns, joins, authorization filters,
transactions, and execution.

The SQL backend is designed for the first two raw-SQL targets:

- SQLite through `SqliteEmitter`, which uses `?` placeholders.
- PostgreSQL through `PostgresEmitter`, which uses `%s` placeholders by default
  for psycopg-style drivers and can also emit `$1`, `$2`, ... placeholders.

## Core idea

A request such as:

```http
GET /items?status__in=free,busy&price__gte=10&sort=-created_at&limit=20
```

is parsed into a backend-neutral AST, then emitted as SQL fragments:

```python
SqlQuery(
    where='"status" IN (?, ?) AND "price" >= ?',
    params=("free", "busy", 10.0),
    order_by=('"created_at" DESC',),
    limit=20,
    offset=0,
    param_style="qmark",
)
```

Values are never interpolated into SQL text. They are returned in `params` and
must be passed to the database driver separately.

## Public SQL objects

```python
from paramora import PostgresEmitter, SqlEmitter, SqlQuery, SqlStatement, SqliteEmitter
```

`SqlQuery` contains generated fragments:

- `where`: predicate expression without the leading `WHERE` keyword
- `params`: bound parameters for the placeholders inside `where`
- `order_by`: ordering expressions without the leading `ORDER BY` keyword
- `limit`: validated limit integer
- `offset`: validated offset integer
- `param_style`: placeholder style used by the output

Convenience methods:

```python
sql.where_clause()          # "WHERE ..." or ""
sql.order_by_clause()       # "ORDER BY ..." or ""
sql.limit_offset_clause()   # "LIMIT ? OFFSET ?", "LIMIT %s OFFSET %s", etc.
sql.statement_params()      # (*sql.params, sql.limit, sql.offset)
```

For simple `SELECT` queries, use `select_statement(...)`:

```python
statement = sql.select_statement("items", columns=("id", "status", "price"))

connection.execute(statement.sql, statement.params)
```

`select_statement(...)` validates and quotes table and column identifiers before
placing them into SQL text.

## SQLite example

```python
from typing import Annotated

from fastapi import Depends, FastAPI
from paramora import CompiledQuery, Query, QueryContract, SqlQuery, SqliteEmitter, query_field

app = FastAPI()


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in", "nin")]
    active: bool
    price: Annotated[float, query_field("eq", "gte", "lte", sortable=True)]


item_query: Query[SqlQuery] = Query(
    ItemQuery,
    emitter=SqliteEmitter(),
    default_limit=20,
    max_limit=100,
)


@app.get("/items")
def list_items(query: CompiledQuery[SqlQuery] = Depends(item_query)):
    sql = query.output
    statement = sql.select_statement(
        "items",
        columns=("id", "status", "active", "price"),
    )
    rows = connection.execute(statement.sql, statement.params).fetchall()
    return [dict(row) for row in rows]
```

Example generated statement:

```python
SqlStatement(
    sql='SELECT "id", "status", "active", "price" FROM "items" '
        'WHERE "status" IN (?, ?) AND "price" >= ? '
        'ORDER BY "price" DESC LIMIT ? OFFSET ?',
    params=("free", "busy", 10.0, 20, 0),
)
```

## PostgreSQL example

For psycopg-style drivers, use `PostgresEmitter()`:

```python
from typing import Annotated

from fastapi import Depends, FastAPI
from paramora import CompiledQuery, PostgresEmitter, Query, QueryContract, SqlQuery, query_field

app = FastAPI()


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in", "nin")]
    active: bool
    price: Annotated[float, query_field("eq", "gte", "lte", sortable=True)]


item_query: Query[SqlQuery] = Query(
    ItemQuery,
    emitter=PostgresEmitter(),
    default_limit=20,
    max_limit=100,
)


@app.get("/items")
def list_items(query: CompiledQuery[SqlQuery] = Depends(item_query)):
    sql = query.output
    statement = sql.select_statement("items", columns=("id", "status", "price"))

    with connection.cursor() as cursor:
        cursor.execute(statement.sql, statement.params)
        rows = cursor.fetchall()

    return rows
```

Example generated statement:

```python
SqlStatement(
    sql='SELECT "id", "status", "price" FROM "items" '
        'WHERE "status" IN (%s, %s) AND "price" >= %s '
        'ORDER BY "price" DESC LIMIT %s OFFSET %s',
    params=("free", "busy", 10.0, 20, 0),
)
```

For drivers that expect PostgreSQL `$1`, `$2`, ... placeholders, configure:

```python
PostgresEmitter(param_style="dollar")
```

## Placeholder styles

Supported positional placeholder styles:

```python
SqliteEmitter()                         # ?
PostgresEmitter()                       # %s
PostgresEmitter(param_style="dollar")   # $1, $2
SqlEmitter(param_style="numeric")       # :1, :2
SqlEmitter(param_style="format")        # %s
SqlEmitter(param_style="qmark")         # ?
```

`SqlQuery.params` is always a positional tuple. Paramora intentionally avoids
named `pyformat` output for now because different drivers handle named parameter
mappings differently. This keeps the initial SQL support predictable and easy to
test.

## Strict mode with SQL

Strict mode is recommended for public SQL APIs:

```python
item_query: Query[SqlQuery] = Query(ItemQuery, emitter=SqliteEmitter())
```

Because a contract is provided, Paramora rejects unknown fields, unsupported
operators, and non-sortable sort fields before SQL is emitted. SQL identifiers
come from the contract and aliases you wrote, not directly from arbitrary client
input.

## Loose mode with SQL

Loose mode is available when you do not pass a contract:

```python
loose_query: Query[SqlQuery] = Query(emitter=SqliteEmitter())
```

Loose mode allows unknown fields, but identifiers are still validated and quoted.
Raw backend operator syntax is still rejected. Values remain strings unless a
field contract exists.

Loose mode is useful for trusted internal tools and prototypes. For public APIs,
prefer strict contracts.

## Identifier safety

SQL identifiers cannot be bound as parameters, so Paramora validates and quotes
identifiers before interpolation.

Safe aliases:

```python
class ItemQuery(QueryContract):
    created_at: Annotated[
        str,
        query_field("gte", "lte", sortable=True, alias="items.created_at"),
    ]
```

This emits:

```sql
"items"."created_at"
```

Unsafe identifiers raise `ValueError` during emission:

```python
query_field("eq", alias="items.status; DROP TABLE items")
```

## Injection resistance

User values are always bound separately:

```http
GET /items?status=free'%20OR%20TRUE%20--
```

emits SQL like:

```python
SqlStatement(
    sql='SELECT "id" FROM "items" WHERE "status" = %s LIMIT %s OFFSET %s',
    params=("free' OR TRUE --", 50, 0),
)
```

The payload is data, not executable SQL, as long as you pass `statement.params`
to the driver instead of string-formatting values into SQL.

Do:

```python
cursor.execute(statement.sql, statement.params)
```

Do not:

```python
statement = f"SELECT * FROM items WHERE status = '{user_status}'"
```

## Testing status

The SQL backend includes:

- emitter tests for placeholder styles, identifier validation, and statement
  composition;
- SQLite integration tests using the standard-library `sqlite3` module;
- PostgreSQL SQL-shape tests for psycopg-style and `$1` placeholder output;
- an optional PostgreSQL integration test that runs only when
  `PARAMORA_POSTGRES_DSN` is configured.

Run the normal SQL tests:

```bash
uv run pytest -vv tests/test_sql_emitter.py tests/test_sql_sqlite.py tests/test_sql_postgres.py
```

Run the optional PostgreSQL integration test:

```bash
PARAMORA_POSTGRES_DSN='postgresql://user:pass@localhost:5432/dbname' \
  uv run pytest -vv -m postgres
```
