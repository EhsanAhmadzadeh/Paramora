<p align="center">
  <a href="https://ehsanahmadzadeh.github.io/Paramora/">
    <img src="https://raw.githubusercontent.com/EhsanAhmadzadeh/Paramora/main/docs/assets/paramora-logo.png" alt="Paramora" width="360">
  </a>
</p>

<p align="center">
  <em>Safe typed filtering for FastAPI, MongoDB, SQL, SQLAlchemy, SQLModel, and ODMs.</em>
</p>

<p align="center">
  <a href="https://github.com/EhsanAhmadzadeh/Paramora/actions/workflows/ci.yml">
    <img src="https://github.com/EhsanAhmadzadeh/Paramora/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://github.com/EhsanAhmadzadeh/Paramora/actions/workflows/pages.yml">
    <img src="https://github.com/EhsanAhmadzadeh/Paramora/actions/workflows/pages.yml/badge.svg" alt="Docs">
  </a>
  <a href="https://codecov.io/gh/EhsanAhmadzadeh/Paramora">
    <img src="https://codecov.io/gh/EhsanAhmadzadeh/Paramora/branch/main/graph/badge.svg" alt="Coverage">
  </a>
  <a href="https://pypi.org/project/paramora/">
    <img src="https://img.shields.io/pypi/v/paramora?color=%2334D058&label=pypi" alt="PyPI">
  </a>
  <a href="https://pypi.org/project/paramora/">
    <img src="https://img.shields.io/pypi/pyversions/paramora.svg?color=%2334D058" alt="Python versions">
  </a>
  <a href="https://github.com/EhsanAhmadzadeh/Paramora/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/EhsanAhmadzadeh/Paramora" alt="License">
  </a>
  <a href="https://github.com/EhsanAhmadzadeh/Paramora">
    <img src="https://img.shields.io/badge/typing-pyright%20strict-blue" alt="Pyright strict">
  </a>
</p>

---

**Paramora** turns user-controlled HTTP query parameters like:

```http
/items?price__gte=10&status__in=free,busy&sort=-created_at&limit=20
```

into safe, typed backend query outputs for MongoDB, raw SQL, SQLAlchemy,
SQLModel, and Mongo ODM adapters.

It helps FastAPI teams avoid hand-written filtering code, unsafe raw backend
query exposure, inconsistent validation, and repeated pagination/sorting logic.

> **Status:** Paramora is alpha software. Public APIs, backend emitter contracts,
> AST details, and error shapes may change before `1.0`.

## Why Paramora?

FastAPI makes endpoint code ergonomic, but filtering APIs often grow into messy
manual parsing:

```python
price = request.query_params.get("price__gte")
status = request.query_params.get("status__in")

query = {}
if price:
    query["price"] = {"$gte": float(price)}
if status:
    query["status"] = {"$in": status.split(",")}
```

Paramora lets you declare the query surface once:

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

Then Paramora handles:

- allowed fields and operators
- type coercion for `str`, `int`, `float`, `bool`, `datetime`, and `Enum`
- strict vs loose validation
- sorting and pagination
- structured FastAPI `422` errors
- MongoDB, raw SQL, SQLAlchemy, SQLModel, and ODM emitter outputs

## Install

```bash
uv add paramora
```

or:

```bash
pip install paramora
```

Optional backend extras:

```bash
uv add "paramora[sqlalchemy]"
uv add "paramora[sqlmodel]"
uv add "paramora[postgres]"
uv add "paramora[odm]"
uv add "paramora[all]"
```

## Requirements

Paramora supports **Python 3.10+** and FastAPI `0.115+`.

Python 3.10 is the compatibility baseline. Runtime code intentionally avoids
Python 3.11+/3.12+ only syntax so a wide range of FastAPI applications can adopt
Paramora.

## MongoDB quickstart

```python
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI
from paramora import CompiledQuery, MongoQuery, Query, QueryContract, query_field

app = FastAPI()


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in")]
    active: bool
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
    price: Annotated[float, query_field("eq", "gt", "gte", "lt", "lte")]


item_query: Query[MongoQuery] = Query(ItemQuery, default_limit=20, max_limit=100)


@app.get("/items")
def list_items(query: CompiledQuery[MongoQuery] = Depends(item_query)):
    mongo = query.output

    docs = (
        collection
        .find(mongo.filter)
        .sort(mongo.sort)
        .skip(mongo.offset)
        .limit(mongo.limit)
    )

    return list(docs)
```

## Raw SQL quickstart

```python
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI
from paramora import CompiledQuery, Query, QueryContract, SqlQuery, SqliteEmitter, query_field

app = FastAPI()


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in")]
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
    price: Annotated[float, query_field("eq", "gte", "lte")]


item_query: Query[SqlQuery] = Query(ItemQuery, emitter=SqliteEmitter())


@app.get("/items")
def list_items(query: CompiledQuery[SqlQuery] = Depends(item_query)):
    sql = query.output
    statement = sql.select_statement("items", columns=("id", "status", "price"))
    rows = connection.execute(statement.text, statement.params).fetchall()
    return [dict(row) for row in rows]
```

Values are always returned as bound parameters. Paramora does not interpolate
user values into SQL strings.

## SQLAlchemy / SQLModel quickstart

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
    return {"sql": str(statement)}
```

## Strict mode and loose mode

- `Query(MyContract)` enables **strict mode**. It rejects unknown fields,
  unsupported operators, invalid values, unsafe sorting, and oversized limits.
- `Query()` enables **loose mode**. It accepts unknown fields for trusted tools
  and prototypes, while still rejecting raw backend operator injection and unsafe
  SQL identifiers.

Use strict mode for public APIs.

## Documentation

The full documentation site is available at:

**https://ehsanahmadzadeh.github.io/Paramora/**

Useful pages:

- [Quickstart](https://ehsanahmadzadeh.github.io/Paramora/quickstart/)
- [Usage guide](https://ehsanahmadzadeh.github.io/Paramora/usage/)
- [How-to guides](https://ehsanahmadzadeh.github.io/Paramora/how-to/)
- [MongoDB backend](https://ehsanahmadzadeh.github.io/Paramora/mongodb/)
- [Raw SQL backend](https://ehsanahmadzadeh.github.io/Paramora/sql/)
- [SQLAlchemy and SQLModel](https://ehsanahmadzadeh.github.io/Paramora/sqlalchemy/)
- [Mongo ODM adapters](https://ehsanahmadzadeh.github.io/Paramora/odms/)
- [Testing strategy](https://ehsanahmadzadeh.github.io/Paramora/testing/)
- [Continuous Integration](https://ehsanahmadzadeh.github.io/Paramora/ci/)
- [Benchmarking](https://ehsanahmadzadeh.github.io/Paramora/benchmarking/)

## Development

```bash
uv sync --group dev --group docs
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -vv
uv run mkdocs build --strict
```

The CI pipeline runs quality gates and the full test suite across every supported
Python version: **3.10, 3.11, 3.12, 3.13, and 3.14**. Coverage is generated on
each Python version and uploaded to Codecov so regressions are visible from the
README badge and pull requests.

The development environment installs the optional backend test dependencies so
SQLAlchemy, SQLModel, MongoDB-compatible `mongomock`, and ODM-related tests can
run when possible.

## Contributing

Paramora is early and contributor-friendly. Good first contributions include:

- improving examples
- adding backend edge-case tests
- improving documentation recipes
- expanding SQLAlchemy / SQLModel coverage
- improving benchmarks and profiling scripts

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Paramora is released under the MIT License.
