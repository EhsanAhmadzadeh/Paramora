# SQLAlchemy and SQLModel

Paramora can compile FastAPI query parameters into SQLAlchemy-compatible query fragments.
This is useful when you already use SQLAlchemy Core, SQLAlchemy ORM, or SQLModel and want Paramora to handle query-parameter validation, coercion, sorting, and pagination.

The SQLAlchemy support is intentionally optional. Paramora does not import SQLAlchemy unless your application chooses to use it.

## Install

```bash
uv add paramora sqlalchemy
```

For SQLModel:

```bash
uv add paramora sqlmodel
```

## SQLAlchemy Core table example

```python
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
def list_items(query: CompiledQuery[SqlAlchemyQuery] = Depends(item_query)):
    statement = query.output.apply(sa.select(items))
    # execute statement with your engine/session
    return {"sql": str(statement)}
```

## SQLAlchemy ORM model example

```python
from datetime import datetime
from typing import Annotated

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from paramora import Query, QueryContract, query_field
from paramora.emitters.sqlalchemy import SqlAlchemyEmitter, SqlAlchemyQuery

class Base(DeclarativeBase):
    pass

class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str]
    price: Mapped[float]
    created_at: Mapped[datetime]

class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in")]
    price: Annotated[float, query_field("gte", "lte")]
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]

item_query: Query[SqlAlchemyQuery] = Query(
    ItemQuery,
    emitter=SqlAlchemyEmitter.from_model(Item),
)
```

## SQLModel example

SQLModel is built on SQLAlchemy, so Paramora uses the same expression emitter.
`SqlModelEmitter` exists as a discoverable alias.

```python
from datetime import datetime
from typing import Annotated

from sqlmodel import Field, SQLModel, select
from paramora import Query, QueryContract, query_field
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

compiled = item_query.parse({"price__gte": "10", "sort": "-created_at"})
statement = compiled.output.apply(select(Item))
```

## What Paramora does and does not do

Paramora emits SQLAlchemy expressions. It does not own your engine, session, transaction, authorization rules, joins, eager loading, or selected columns.

This keeps Paramora focused:

- validate query parameters;
- coerce values into Python types;
- enforce allowed fields and operators in strict mode;
- generate safe SQLAlchemy/SQLModel expressions;
- apply sort, limit, and offset.

Your application remains responsible for tenancy predicates, permissions, joins, and execution.
