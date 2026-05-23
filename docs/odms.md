# ODMs and Mongo-style adapters

Paramora's Mongo backend already emits normal MongoDB filter dictionaries and sort pairs. Many ODMs can consume those directly or with a small adapter.

For convenience, Paramora includes `MongoOdmEmitter`, which wraps the regular Mongo output and exposes common helper formats for ODMs such as Beanie and MongoEngine.

## Install

The adapter itself has no extra runtime dependency:

```bash
uv add paramora
```

If your application uses an ODM, install that ODM separately:

```bash
uv add beanie
# or
uv add mongoengine
```

## Mongo ODM adapter example

```python
from typing import Annotated

from fastapi import Depends, FastAPI
from paramora import CompiledQuery, Query, QueryContract, query_field
from paramora.emitters.odm import MongoOdmEmitter, MongoOdmQuery

class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in")]
    created_at: Annotated[str, query_field("eq", sortable=True)]

item_query: Query[MongoOdmQuery] = Query(
    ItemQuery,
    emitter=MongoOdmEmitter(),
)

app = FastAPI()

@app.get("/items")
def list_items(query: CompiledQuery[MongoOdmQuery] = Depends(item_query)):
    mongo = query.output
    return {
        "filter": mongo.filter,
        "beanie_sort": mongo.beanie_sort(),
        "limit": mongo.limit,
        "offset": mongo.offset,
    }
```

## Beanie-style sort helper

```python
compiled = item_query.parse({"status__in": "free,busy", "sort": "-created_at"})
odm = compiled.output

assert odm.filter == {"status": {"$in": ["free", "busy"]}}
assert odm.beanie_sort() == ("-created_at",)
```

## MongoEngine-style order helper

```python
compiled = item_query.parse({"sort": "-created_at"})
odm = compiled.output

assert odm.mongoengine_order_by() == ("-created_at",)
```

## Why this is adapter-based

Mongo ODMs differ in how they represent queries, sessions, projections, eager loading, and execution. Paramora therefore does not try to own the ODM query lifecycle.

The safe boundary is:

1. Paramora validates HTTP query parameters.
2. Paramora compiles them into Mongo-compatible filter/sort/pagination data.
3. Your application passes that data into the ODM in the way that best matches your model and session lifecycle.
