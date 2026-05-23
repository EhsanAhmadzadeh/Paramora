from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlmodel import Field, SQLModel, select

from paramora import CompiledQuery, Query, QueryContract, query_field
from paramora.emitters.sqlalchemy import SqlAlchemyQuery, SqlModelEmitter


class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: str
    price: float
    created_at: datetime


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in")]
    price: Annotated[float, query_field("gte", "lte")]
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]


item_query: Query[SqlAlchemyQuery] = Query(
    ItemQuery,
    emitter=SqlModelEmitter.from_model(Item),
)

app = FastAPI()


@app.get("/items")
def list_items(
    query: CompiledQuery[SqlAlchemyQuery] = Depends(item_query),
) -> dict[str, str]:
    statement = query.output.apply(select(Item))
    return {"sql": str(statement)}
