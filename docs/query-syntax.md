# Query syntax

Paramora uses a small backend-neutral HTTP query syntax. Clients do not send raw
MongoDB operators or SQL fragments. They send field names, operator suffixes,
sort directives, and pagination values.

## Filter syntax

The default operator is equality:

```http
/items?status=free
```

This is equivalent to:

```http
/items?status__eq=free
```

Other operators use Django-style double-underscore suffixes:

```http
/items?price__gte=10&price__lt=100
```

## Supported operators

| Operator | Query parameter | Meaning |
| --- | --- | --- |
| `eq` | `field=value` or `field__eq=value` | equal to |
| `ne` | `field__ne=value` | not equal to |
| `gt` | `field__gt=value` | greater than |
| `gte` | `field__gte=value` | greater than or equal to |
| `lt` | `field__lt=value` | less than |
| `lte` | `field__lte=value` | less than or equal to |
| `in` | `field__in=a,b,c` | value is in list |
| `nin` | `field__nin=a,b,c` | value is not in list |

## Equality

```http
/items?status=free&active=true
```

With a strict contract, Paramora coerces values using the declared field types.
For example, `active=true` becomes `True` when `active` is declared as `bool`.

## Range filters

```http
/items?price__gte=10&price__lt=100
```

MongoDB output merges range operators on the same field:

```python
{"price": {"$gte": 10.0, "$lt": 100.0}}
```

SQL output combines predicates with `AND`:

```sql
"price" >= ? AND "price" < ?
```

## List filters

`in` and `nin` use comma-separated values:

```http
/items?status__in=free,busy
/items?status__nin=archived,deleted
```

Empty list filters are rejected:

```http
/items?status__in=,,
```

In strict mode, every list item is coerced using the declared field type.

## Sorting

Sorting uses the reserved `sort` parameter.

Ascending:

```http
/items?sort=created_at
```

Descending:

```http
/items?sort=-created_at
```

In strict mode, the field must be declared with `sortable=True`:

```python
class ItemQuery(QueryContract):
    created_at: Annotated[datetime, query_field("gte", "lte", sortable=True)]
```

Sorting is opt-in because it can affect backend indexes and query performance.

## Pagination

Paramora reserves `limit` and `offset`:

```http
/items?limit=20&offset=40
```

`Query` controls defaults and limits:

```python
item_query = Query(ItemQuery, default_limit=20, max_limit=100)
```

Rules:

- missing `limit` uses `default_limit`
- missing `offset` uses `0`
- both values must be integers
- both values must be greater than or equal to zero
- `limit` cannot exceed `max_limit`

## Reserved parameters

These names are reserved by Paramora:

```text
sort, limit, offset
```

They are not parsed as filter fields.

## Repeated parameters

When parsing a mapping-like input, Paramora currently uses the last value for a
repeated parameter. FastAPI integration receives repeated query parameters via
`request.query_params.multi_items()` and applies the same effective behavior.

For list filters, prefer comma-separated values:

```http
/items?status__in=free,busy
```

rather than repeated keys.

## Strict mode behavior

In strict mode, query parameters are validated against the declared contract.

```python
item_query = Query(ItemQuery)
```

Strict mode rejects:

- unknown fields
- unknown operators
- known operators that are not allowed for that field
- invalid values
- sorting by unknown or non-sortable fields
- missing required filters
- raw backend operator syntax

Example error:

```json
{
  "detail": [
    {
      "loc": ["query", "status__gte"],
      "msg": "Operator 'gte' is not allowed for field 'status'.",
      "type": "query.operator_not_allowed",
      "input": "free"
    }
  ]
}
```

## Loose mode behavior

Loose mode is enabled with no contract:

```python
query = Query()
```

Loose mode allows unknown fields and known Paramora operators. Unknown values are
usually emitted as strings.

Loose mode still rejects raw backend syntax:

```http
/items?$where=...
/items?price[$gte]=10
/items?price__$gte=10
```

Loose mode is less schema-strict, not unsafe raw database passthrough.

## Backend-neutral design

These query parameters are the same whether the backend is MongoDB or SQL:

```http
/items?status__in=free,busy&price__gte=10&sort=-created_at&limit=20
```

Only the emitter changes:

```python
mongo_query = Query(ItemQuery)
sql_query = Query(ItemQuery, emitter=SqlEmitter())
```
