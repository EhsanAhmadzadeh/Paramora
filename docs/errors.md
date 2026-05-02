# Error handling

Paramora uses structured validation errors. The error format is intentionally
similar to FastAPI/Pydantic-style errors so API clients can inspect `loc`, `msg`,
`type`, and optionally `input`.

## FastAPI behavior

When `Query` is used as a FastAPI dependency, validation failures become HTTP
`422` responses.

```python
@app.get("/items")
def list_items(query: CompiledQuery[MongoQuery] = Depends(item_query)):
    ...
```

Invalid request:

```http
GET /items?price=bad
```

Response:

```json
{
  "detail": [
    {
      "loc": ["query", "price"],
      "msg": "Expected a float-compatible value.",
      "type": "query.type_error.float",
      "input": "bad"
    }
  ]
}
```

## Direct parsing behavior

When you call `Query.parse(...)` directly, Paramora raises
`QueryValidationError`.

```python
from paramora import QueryValidationError

try:
    item_query.parse({"price": "bad"})
except QueryValidationError as exc:
    errors = exc.to_list()
```

`exc.to_list()` returns JSON-compatible dictionaries.

## Error shape

Each error contains:

```json
{
  "loc": ["query", "price__gte"],
  "msg": "Expected a float-compatible value.",
  "type": "query.type_error.float",
  "input": "bad"
}
```

Fields:

- `loc`: where the error happened, usually `['query', '<parameter>']`
- `msg`: human-readable message
- `type`: stable machine-readable error code
- `input`: offending input value when available

## Common errors

### Unknown field

Strict mode rejects fields not declared in the contract.

```http
/items?password=secret
```

```json
{
  "loc": ["query", "password"],
  "msg": "Unknown filter field.",
  "type": "query.unknown_field",
  "input": "secret"
}
```

### Unknown operator

```http
/items?price__between=10,20
```

```json
{
  "loc": ["query", "price__between"],
  "msg": "Unknown operator 'between'.",
  "type": "query.unknown_operator",
  "input": "10,20"
}
```

### Operator not allowed

If `status` only allows `eq` and `in`, this is invalid:

```http
/items?status__gte=free
```

```json
{
  "loc": ["query", "status__gte"],
  "msg": "Operator 'gte' is not allowed for field 'status'.",
  "type": "query.operator_not_allowed",
  "input": "free"
}
```

### Type error

```http
/items?price=bad
```

```json
{
  "loc": ["query", "price"],
  "msg": "Expected a float-compatible value.",
  "type": "query.type_error.float",
  "input": "bad"
}
```

Other type errors include:

```text
query.type_error.int
query.type_error.float
query.type_error.bool
query.type_error.datetime
query.type_error.enum
```

### Empty list

```http
/items?status__in=,,
```

```json
{
  "loc": ["query", "status__in"],
  "msg": "Expected at least one comma-separated value.",
  "type": "query.empty_list",
  "input": ",,"
}
```

### Required field missing

```python
class ItemQuery(QueryContract):
    tenant_id: Annotated[str, query_field(required=True)]
```

```json
{
  "loc": ["query", "tenant_id"],
  "msg": "Required filter field is missing.",
  "type": "query.required"
}
```

### Invalid sort

Sorting by a field that is unknown or not sortable raises a structured error.

```http
/items?sort=password
```

Possible strict-mode error:

```json
{
  "loc": ["query", "sort"],
  "msg": "Sorting is not allowed for field 'password'.",
  "type": "query.sort_not_allowed",
  "input": "password"
}
```

### Pagination errors

Invalid pagination values raise errors such as:

```text
query.type_error.limit
query.type_error.offset
query.limit_too_large
query.limit_negative
query.offset_negative
```

## Multiple errors

Paramora collects validation errors where practical and returns them together.
This helps clients fix multiple query issues in one round trip.

## Security-related errors

Paramora rejects raw backend operator syntax even in loose mode.

Examples:

```http
/items?$where=...
/items?price[$gte]=10
/items?price__$gte=10
```

These errors protect the boundary between HTTP query syntax and backend-specific
query languages.

## Stability

Error codes are part of Paramora's public API direction. During alpha releases,
error shapes may still change, but the goal is to stabilize them before `1.0`.
When changing an error code or payload shape, update tests, docs, and release
notes.
