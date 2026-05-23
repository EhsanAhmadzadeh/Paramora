# Paramora

<p align="center">
  <img src="assets/paramora-logo.png" alt="Paramora logo" width="320">
</p>

<p align="center">
  <strong>Safe typed filtering for FastAPI.</strong>
</p>

Paramora turns HTTP query parameters such as
`?price__gte=10&status__in=free,busy&sort=-created_at` into typed backend
outputs for MongoDB, raw SQL, SQLAlchemy, SQLModel, and Mongo ODM adapters.

It is built for FastAPI applications that need filtering, sorting, pagination,
validation, and backend query generation without exposing raw backend syntax to
API clients.

## Why use Paramora?

Most filtering endpoints eventually repeat the same work:

- parse query strings
- validate allowed fields and operators
- coerce strings into `bool`, `int`, `float`, `datetime`, or `Enum`
- reject unsafe backend syntax
- build MongoDB dictionaries, SQL fragments, or ORM expressions
- keep error responses consistent

Paramora makes that flow explicit and reusable.

```python
from datetime import datetime
from typing import Annotated

from paramora import Query, QueryContract, query_field


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in")]
    active: bool
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
    price: Annotated[float, query_field("eq", "gte", "lte")]


item_query = Query(ItemQuery)
```

## Backends

Paramora currently supports:

| Backend | Output | Use case |
| --- | --- | --- |
| MongoDB | `MongoQuery` | PyMongo-style filtering, sorting, skip, limit |
| Raw SQL | `SqlQuery` | SQLite and PostgreSQL-style parameterized SQL |
| SQLAlchemy | `SqlAlchemyQuery` | SQLAlchemy Core and ORM expressions |
| SQLModel | `SqlAlchemyQuery` | SQLModel statements built on SQLAlchemy |
| Mongo ODM adapters | `MongoOdmQuery` | Beanie/MongoEngine-friendly helpers |

## Start here

- [Quickstart](quickstart.md)
- [Usage guide](usage.md)
- [How-to guides](how-to.md)
- [Query contracts](contracts.md)
- [Query syntax](query-syntax.md)

## Backend guides

- [MongoDB](mongodb.md)
- [Raw SQL](sql.md)
- [SQLAlchemy and SQLModel](sqlalchemy.md)
- [Mongo ODM adapters](odms.md)

## Reliability

- [Error handling](errors.md)
- [Testing strategy](testing.md)
- [Continuous Integration](ci.md)
- [Benchmarking](benchmarking.md)
- [Profiling and future Rust hotspots](profiling-and-rust.md)
- [Python support](python-support.md)
- [Development with uv](development.md)
- [Changelog](changelog.md)

## Project status

Paramora is alpha software. Public APIs, backend emitter contracts, AST details,
and error shapes may change before `1.0`.
