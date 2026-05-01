# Error handling

Paramora treats error details as part of its public API. Core parsing raises
`QueryValidationError`. FastAPI dependencies convert that exception into a 422
HTTP response.

## Shape

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

Each error contains:

- `loc`: location path, usually `["query", "param_name"]`
- `msg`: human-readable message
- `type`: stable machine-readable error code
- `input`: the rejected input when useful

## Current error codes

- `query.empty_list`
- `query.invalid_field`
- `query.invalid_operator`
- `query.invalid_sort_field`
- `query.limit_too_large`
- `query.operator_not_allowed`
- `query.raw_operator_not_allowed`
- `query.required`
- `query.sort_not_allowed`
- `query.type_error.bool`
- `query.type_error.datetime`
- `query.type_error.enum`
- `query.type_error.float`
- `query.type_error.int`
- `query.unknown_field`
- `query.unknown_operator`
- `query.unknown_sort_field`
- `query.value_error.non_negative`

New codes may be added as Paramora grows. Existing codes should remain stable
or change only with an explicit compatibility note.
