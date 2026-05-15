# How-to guides

This page is organized around practical questions you are likely to have while
adding Paramora to a FastAPI application. It focuses on copyable patterns and the
reasoning behind them.

## How do I choose strict mode or loose mode?

Use **strict mode** for public APIs. Strict mode starts when you pass a
`QueryContract` to `Query`:

```python
item_query = Query(ItemQuery)
```

Strict mode means Paramora rejects unknown fields, unsupported operators,
invalid values, non-sortable sort fields, and oversized limits before your
backend sees the request.

Use **loose mode** only when you do not have a contract yet:

```python
item_query = Query()
```

Loose mode accepts unknown fields, but it still rejects raw backend operator
syntax and unsafe SQL identifiers. It is useful for internal tools, prototypes,
and trusted admin dashboards. It is not the recommended default for public APIs.

## How do I expose a safe MongoDB filter endpoint?

Define a contract, choose allowed operators per field, and use the default Mongo
emitter.

```python
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI
from paramora import CompiledQuery, MongoQuery, Query, QueryContract, query_field

app = FastAPI()


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in", "nin")]
    active: bool
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
    price: Annotated[float, query_field("eq", "gte", "lte")]


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

A request like this:

```http
GET /items?status__in=free,busy&price__gte=10&sort=-created_at
```

produces a safe `MongoQuery` object. Raw Mongo operators such as `$where` or
`price[$gte]` are not accepted from HTTP query parameters.

## How do I expose a raw SQLite endpoint?

Use `SqliteEmitter`. Paramora generates SQL fragments and bound parameters, not a
connection or cursor.

```python
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI
from paramora import CompiledQuery, Query, QueryContract, SqlQuery, SqliteEmitter, query_field

app = FastAPI()


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in", "nin")]
    active: bool
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
    price: Annotated[float, query_field("eq", "gte", "lte")]


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
        columns=("id", "status", "active", "created_at", "price"),
    )
    rows = connection.execute(statement.sql, statement.params).fetchall()
    return [dict(row) for row in rows]
```

Generated SQLite uses `?` placeholders:

```python
statement.sql
# SELECT "id", "status", "active", "created_at", "price" FROM "items"
# WHERE "status" IN (?, ?) AND "price" >= ?
# ORDER BY "created_at" DESC LIMIT ? OFFSET ?

statement.params
# ("free", "busy", 10.0, 20, 0)
```

## How do I expose a raw PostgreSQL endpoint?

Use `PostgresEmitter`. By default it emits psycopg-compatible `%s` placeholders.

```python
from typing import Annotated

from fastapi import Depends, FastAPI
from paramora import CompiledQuery, PostgresEmitter, Query, QueryContract, SqlQuery, query_field

app = FastAPI()


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in", "nin")]
    price: Annotated[float, query_field("eq", "gte", "lte", sortable=True)]


item_query: Query[SqlQuery] = Query(
    ItemQuery,
    emitter=PostgresEmitter(),
    default_limit=20,
    max_limit=100,
)


@app.get("/items")
def list_items(query: CompiledQuery[SqlQuery] = Depends(item_query)):
    statement = query.output.select_statement("items", columns=("id", "status", "price"))
    with connection.cursor() as cursor:
        cursor.execute(statement.sql, statement.params)
        return cursor.fetchall()
```

Use `PostgresEmitter(param_style="dollar")` if your driver expects `$1`, `$2`,
... placeholders instead of `%s`.

## How do I add authorization predicates to SQL?

Paramora intentionally does not own authorization. Compose your required
predicate around Paramora's generated fragment.

```python
sql = query.output
where_parts = ['"tenant_id" = ?']
params: list[object] = [current_tenant_id]

if sql.where:
    where_parts.append(sql.where)
    params.extend(sql.params)

statement = (
    'SELECT "id", "status", "price" FROM "items" '
    f'WHERE {" AND ".join(where_parts)} '
    f'{sql.order_by_clause()} '
    f'{sql.limit_offset_clause()}'
)
params.extend((sql.limit, sql.offset))
```

For PostgreSQL, use the same idea but match the placeholder style. If you use
Paramora's `select_statement(...)`, add authorization outside it or define a
small application helper that composes your own full statement.

## How do I map API names to database column names?

Use `alias` in `query_field(...)`.

```python
class ItemQuery(QueryContract):
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True, alias="items.created_at"),
    ]
```

The HTTP API still uses `created_at`:

```http
GET /items?created_at__gte=2026-01-01T00:00:00&sort=-created_at
```

The SQL backend emits the alias as a validated quoted identifier:

```sql
"items"."created_at"
```

The MongoDB backend uses the alias as the emitted field path.

## How do I require a filter?

Use `required=True` for fields that must appear in the query string.

```python
class ItemQuery(QueryContract):
    tenant_id: Annotated[str, query_field(required=True)]
    status: Annotated[str, query_field("eq", "in")]
```

Missing required fields produce a structured validation error before backend
emission.

## How do I add sorting safely?

Sorting is opt-in for strict contracts.

```python
class ItemQuery(QueryContract):
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
```

Clients can then use:

```http
GET /items?sort=created_at
GET /items?sort=-created_at
```

A non-sortable field is rejected in strict mode.

## How do I control pagination?

Set `default_limit` and `max_limit` on `Query`.

```python
item_query = Query(ItemQuery, default_limit=25, max_limit=100)
```

Paramora accepts:

```http
GET /items?limit=50&offset=100
```

`limit` must be positive and less than or equal to `max_limit`. `offset` must be
non-negative.

## How do I inspect errors?

Direct use of `Query.parse(...)` raises `QueryValidationError`:

```python
from paramora import QueryValidationError

try:
    compiled = item_query.parse({"price": "not-a-float"})
except QueryValidationError as exc:
    errors = exc.to_list()
```

FastAPI dependency usage turns the same errors into an HTTP `422` response.

## How do I benchmark my changes?

Run the full benchmark suite before and after a performance-sensitive change:

```bash
uv run python benchmarks/bench_all.py --json benchmark-results/before.json
uv run python benchmarks/bench_all.py --json benchmark-results/after.json
uv run python benchmarks/compare_results.py benchmark-results/before.json benchmark-results/after.json
```

Use cProfile when a scenario gets slower:

```bash
uv run python benchmarks/profile_parse.py --scenario strict-sql --iterations 500000 --limit 40
```

Optimize only after a benchmark or profile shows a real hotspot.
