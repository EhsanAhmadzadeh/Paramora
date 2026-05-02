# MongoDB backend

MongoDB is Paramora's default backend. If you do not pass an emitter to `Query`,
Paramora emits `MongoQuery` objects.

```python
item_query: Query[MongoQuery] = Query(ItemQuery)
```

## Output shape

```python
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MongoQuery:
    filter: dict[str, Any]
    sort: list[tuple[str, int]]
    limit: int
    offset: int
```

`MongoQuery` is designed for PyMongo-style collection APIs:

```python
mongo = query.output

docs = (
    collection
    .find(mongo.filter)
    .sort(mongo.sort)
    .skip(mongo.offset)
    .limit(mongo.limit)
)
```

## Complete FastAPI example

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

## Operator emission

| Paramora operator | MongoDB output |
| --- | --- |
| `eq` | direct field value |
| `ne` | `$ne` |
| `gt` | `$gt` |
| `gte` | `$gte` |
| `lt` | `$lt` |
| `lte` | `$lte` |
| `in` | `$in` |
| `nin` | `$nin` |

## Equality filters

Request:

```http
/items?status=free&active=true
```

Output:

```python
MongoQuery(
    filter={"status": "free", "active": True},
    sort=[],
    limit=20,
    offset=0,
)
```

## Range filters

Request:

```http
/items?price__gte=10&price__lt=100
```

Output:

```python
MongoQuery(
    filter={"price": {"$gte": 10.0, "$lt": 100.0}},
    sort=[],
    limit=20,
    offset=0,
)
```

Range filters on the same field are merged into one MongoDB operator document.

## List filters

Request:

```http
/items?status__in=free,busy
```

Output:

```python
MongoQuery(
    filter={"status": {"$in": ["free", "busy"]}},
    sort=[],
    limit=20,
    offset=0,
)
```

`nin` emits `$nin`.

## Sorting and pagination

Request:

```http
/items?sort=-created_at&limit=10&offset=20
```

Output:

```python
MongoQuery(
    filter={},
    sort=[("created_at", -1)],
    limit=10,
    offset=20,
)
```

Descending sort uses `-1`; ascending sort uses `1`.

## Aliases

Use aliases when public query names differ from MongoDB field names.

```python
class ItemQuery(QueryContract):
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True, alias="createdAt"),
    ]
```

Clients still use the public name:

```http
/items?created_at__gte=2026-01-01T00:00:00Z&sort=-created_at
```

MongoDB receives the alias:

```python
MongoQuery(
    filter={"createdAt": {"$gte": datetime(...)}},
    sort=[("createdAt", -1)],
    limit=20,
    offset=0,
)
```

## Strict mode and MongoDB

Strict mode is recommended for public MongoDB-backed APIs:

```python
item_query = Query(ItemQuery)
```

It prevents accidental exposure of fields that should not be filterable, such as
password hashes, internal flags, or authorization-sensitive attributes.

## Loose mode and MongoDB

Loose mode can be useful for internal tools:

```python
loose_query: Query[MongoQuery] = Query(default_limit=20, max_limit=100)
```

It accepts unknown fields, but still rejects raw MongoDB syntax such as:

```http
/items?$where=...
/items?price[$gte]=10
/items?price__$gte=10
```

Loose mode is less strict, not raw MongoDB passthrough.

## Testing MongoDB behavior

Paramora's test suite uses `mongomock` integration tests to execute emitted
MongoDB query objects against an in-memory collection. These tests cover equality,
list operators, range filters, booleans, datetime ranges, sorting, pagination,
and combined queries.

Run Mongo-specific tests with:

```bash
uv run pytest -vv tests/test_mongo_mongomock.py
```
