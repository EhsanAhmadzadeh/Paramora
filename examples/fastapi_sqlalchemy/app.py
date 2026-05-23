from __future__ import annotations

from datetime import datetime
from typing import Annotated

import sqlalchemy as sa
from fastapi import Depends, FastAPI

from paramora import CompiledQuery, Query, QueryContract, query_field
from paramora.emitters.sqlalchemy import SqlAlchemyEmitter, SqlAlchemyQuery

metadata = sa.MetaData()
items = sa.Table(
    "items",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("status", sa.String),
    sa.Column("price", sa.Float),
    sa.Column("created_at", sa.DateTime),
)


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in")]
    price: Annotated[float, query_field("gte", "lte")]
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]


item_query: Query[SqlAlchemyQuery] = Query(
    ItemQuery,
    emitter=SqlAlchemyEmitter.from_table(items),
)

app = FastAPI()


@app.get("/items")
def list_items(
    query: CompiledQuery[SqlAlchemyQuery] = Depends(item_query),
) -> dict[str, str]:
    statement = query.output.apply(sa.select(items))
    return {"sql": str(statement)}
