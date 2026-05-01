# Query syntax

Paramora uses Django-style query operators.

```http
/items?status__in=free,busy&active=true&price__gte=10&sort=-created_at&limit=20&offset=0
```

## Filters

A bare field means equality:

```http
/items?active=true
```

is equivalent to:

```http
/items?active__eq=true
```

Supported operators:

| Operator | Meaning |
| --- | --- |
| `eq` | equals |
| `ne` | not equals |
| `gt` | greater than |
| `gte` | greater than or equal |
| `lt` | less than |
| `lte` | less than or equal |
| `in` | comma-separated inclusion list |
| `nin` | comma-separated exclusion list |

## Sorting

```http
/items?sort=created_at
/items?sort=-created_at
/items?sort=status,-created_at
```

A leading `-` means descending order. Without `-`, sorting is ascending.

## Pagination

```http
/items?limit=20&offset=40
```

`limit` and `offset` must be non-negative integers. `limit` cannot exceed the
`max_limit` configured on `Query`.
