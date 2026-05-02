# Query contracts

A query contract is the public query surface for an endpoint. It describes field
names, value types, allowed operators, sortability, backend aliases, and required
filters.

```python
from datetime import datetime
from typing import Annotated

from paramora import QueryContract, query_field


class ItemQuery(QueryContract):
    status: Annotated[str, query_field("eq", "in", "nin")]
    active: bool
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
    price: Annotated[float, query_field("eq", "gt", "gte", "lt", "lte")]
```

## Bare annotations

A bare annotation means equality only:

```python
active: bool
```

This accepts `?active=true` and `?active__eq=true`.

## Field metadata

Use `query_field(...)` inside `typing.Annotated` for Paramora metadata:

```python
created_at: Annotated[
    datetime,
    query_field("gte", "lte", sortable=True, alias="createdAt"),
]
```

Arguments:

- positional operators: allowed filter operators for the field
- `sortable`: whether the field may be used in `sort`
- `alias`: backend field name used by emitters
- `required`: whether at least one filter for this field must be present

## Why Annotated?

Do this:

```python
created_at: Annotated[datetime, query_field("gte", "lte")]
```

Do not do this:

```python
created_at: datetime = query_field("gte", "lte")
```

The `Annotated` style keeps type checkers aware that `created_at` is a
`datetime`, not a Paramora metadata object.

## Unsupported annotations

Container annotations such as `list[str]` are intentionally unsupported in 0.x.
Use `in` and `nin` operators for list semantics at the query syntax layer.
