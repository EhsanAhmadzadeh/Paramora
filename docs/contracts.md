# Query contracts

A query contract is a class that declares the fields, types, operators, aliases,
sorting behavior, and required filters for an endpoint.

Contracts are used by strict mode:

```python
item_query = Query(ItemQuery)
```

No contract means loose mode:

```python
loose_query = Query()
```

## Basic contract

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

## Bare annotations

A bare annotation creates an equality-only field.

```python
class ItemQuery(QueryContract):
    active: bool
```

This accepts:

```http
/items?active=true
```

It rejects:

```http
/items?active__ne=true
```

because `ne` was not explicitly allowed.

## `query_field(...)`

Use `query_field(...)` inside `typing.Annotated` when the field needs metadata.

```python
class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in", "nin")]
```

The first positional arguments are allowed operators. The supported operators are:

```text
eq, ne, gt, gte, lt, lte, in, nin
```

The function also accepts keyword metadata:

```python
query_field(
    "gte",
    "lte",
    sortable=True,
    alias="createdAt",
    required=True,
)
```

## Why `Annotated`?

This style keeps type checkers happy.

Good:

```python
class ItemQuery(QueryContract):
    created_at: Annotated[datetime, query_field("gte", "lte")]
```

The field is still understood as `datetime` by type checkers.

Avoid assignment-style metadata:

```python
# Not the Paramora style.
created_at: datetime = query_field("gte", "lte")
```

That makes editors and type checkers see a `QueryFieldInfo` assigned to a
`datetime` field.

## Supported field types

Paramora supports:

- `str`
- `int`
- `float`
- `bool`
- `datetime.datetime`
- simple `enum.Enum` subclasses

For `in` and `nin`, comma-separated values are parsed as lists and each element
is coerced using the field type.

## Strings

```python
class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in", "nin")]
```

```http
/items?status__in=free,busy
```

emits values like:

```python
["free", "busy"]
```

## Numbers

```python
class ItemQuery(QueryContract):
    price: Annotated[float, query_field("eq", "gt", "gte", "lt", "lte")]
    quantity: Annotated[int, query_field("eq", "gte", "lte")]
```

```http
/items?price__gte=10.5&quantity__lte=100
```

Invalid numbers produce structured errors such as `query.type_error.float`.

## Booleans

```python
class ItemQuery(QueryContract):
    active: bool
```

Accepted true values:

```text
true, 1, yes, on
```

Accepted false values:

```text
false, 0, no, off
```

Parsing is case-insensitive.

## Datetimes

```python
class ItemQuery(QueryContract):
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
```

```http
/items?created_at__gte=2026-01-01T12:30:00Z
```

Paramora uses standard-library ISO-8601 parsing. A trailing `Z` is treated as
UTC.

## Enums

```python
from enum import Enum
from typing import Annotated


class Status(Enum):
    FREE = "free"
    BUSY = "busy"


class ItemQuery(QueryContract):
    status: Annotated[Status, query_field("eq", "in")]
```

```http
/items?status=free
/items?status__in=free,busy
```

Invalid enum values raise `query.type_error.enum`.

## Sorting

Fields are not sortable by default. Enable sorting explicitly:

```python
class ItemQuery(QueryContract):
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
```

Now these are allowed:

```http
/items?sort=created_at
/items?sort=-created_at
```

Sorting should be opt-in because it can affect indexes and query performance.

## Required fields

Required fields are useful for safety filters such as tenant IDs.

```python
class ItemQuery(QueryContract):
    tenant_id: Annotated[str, query_field(required=True)]
    status: Annotated[str, query_field("eq", "in")]
```

If the request omits `tenant_id`, Paramora raises:

```json
{
  "detail": [
    {
      "loc": ["query", "tenant_id"],
      "msg": "Required filter field is missing.",
      "type": "query.required"
    }
  ]
}
```

## Backend aliases

Aliases map public query names to backend names.

MongoDB:

```python
class ItemQuery(QueryContract):
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True, alias="createdAt"),
    ]
```

Request clients use `created_at`:

```http
/items?created_at__gte=2026-01-01T00:00:00Z&sort=-created_at
```

MongoDB receives `createdAt`.

SQL:

```python
class ItemQuery(QueryContract):
    created_at: Annotated[
        datetime,
        query_field("gte", "lte", sortable=True, alias="items.created_at"),
    ]
```

SQL output uses:

```sql
"items"."created_at"
```

## Contract design guidance

For public APIs:

- prefer strict mode with a contract
- allow only the operators the endpoint actually needs
- mark sorting fields explicitly
- consider required tenant/user filters for multi-tenant systems
- use aliases to decouple public API names from backend names
- keep raw backend syntax out of query parameters
