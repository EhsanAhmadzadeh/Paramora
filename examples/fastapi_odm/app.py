from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI

from paramora import CompiledQuery, Query, QueryContract, query_field
from paramora.emitters.odm import MongoOdmEmitter, MongoOdmQuery


class ItemQuery(QueryContract):  # noqa: D101
    status: Annotated[str, query_field("eq", "in")]
    created_at: Annotated[str, query_field("eq", sortable=True)]


item_query: Query[MongoOdmQuery] = Query(ItemQuery, emitter=MongoOdmEmitter())
app = FastAPI()


@app.get("/items")
def list_items(  # noqa: D103
    query: CompiledQuery[MongoOdmQuery] = Depends(item_query),
) -> dict[str, object]:
    odm = query.output
    return {
        "filter": odm.filter,
        "beanie_sort": odm.beanie_sort(),
        "mongoengine_order_by": odm.mongoengine_order_by(),
        "limit": odm.limit,
        "offset": odm.offset,
    }
