# Query contracts

A query contract is the public query surface for an endpoint. It describes field
names, value types, allowed operators, sortability, backend aliases, and required
filters.

## Basic contract

```python
from paramora import QueryContract

class ItemQuery(QueryContract):
    active: bool
    status: str
```

Bare fields allow equality only. This means `?active=true` and `?status=free`
are accepted, but `?status__in=free,busy` is rejected unless `in` is declared.

## Operators

```python
from typing import Annotated
from paramora import QueryContract, query_field

class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in", "nin")]
```

Operators are positional string literals for editor autocomplete. Supported 0.1
operators are `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, and `nin`.

## Sorting

```python
class ItemQuery(QueryContract):
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
```

Contract-backed strict mode only allows sorting on fields marked as sortable.

## Aliases

Aliases map public query names to backend field names during emission:

```python
class ItemQuery(QueryContract):
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True, alias="createdAt"),
    ]
```

The AST keeps the public field name. The MongoDB emitter applies the alias.

## Required filters

```python
class ItemQuery(QueryContract):
    tenant_id: Annotated[str, query_field(required=True)]
```

Required filters are useful for guardrails such as tenant scoping. If the field
is missing, Paramora returns `query.required`.

## Unsupported annotations

Container annotations such as `list[str]` are intentionally unsupported in 0.1.
Use `in` and `nin` operators for list semantics at the query syntax layer.
