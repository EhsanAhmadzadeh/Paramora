# Quickstart

Paramora compiles FastAPI query parameters into backend query objects. The first
backend is MongoDB.

## Install

The package is not published yet. When it is available, install it with uv:

```bash
uv add paramora
```

For local development from the repository:

```bash
uv sync --group dev
```

## Define a contract

Use a `QueryContract` class to declare which query parameters are allowed.
Bare annotations accept equality filters. Use `Annotated[..., query_field(...)]`
when the field needs extra operators, sort support, aliases, or required
behavior.

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

## Use it in FastAPI

```python
from fastapi import Depends, FastAPI
from paramora import CompiledQuery, Query

app = FastAPI()
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


## Try a request

```http
/items?status__in=free,busy&price__gte=10&sort=-created_at&limit=20
```

Paramora validates, coerces, builds an AST, and emits a MongoDB query object.
