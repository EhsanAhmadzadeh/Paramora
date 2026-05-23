# Paramora architecture

Paramora compiles FastAPI query parameters through a small, explicit pipeline:

```text
HTTP query params
→ Query / QueryContract
→ QueryParser
→ backend-neutral QueryAst
→ configured backend emitter
→ CompiledQuery[BackendOutput]
```

The central rule is that Paramora never parses request parameters directly into
MongoDB dictionaries, SQL strings, or any other backend-specific representation.
Request syntax is parsed into a backend-neutral AST first. Emitters are the only
layer that knows how a backend represents filters, sort, limit, and offset.

## Python compatibility

Paramora targets Python `3.10+`. The code intentionally avoids syntax that would
exclude 3.10 and 3.11 users, including PEP 695 `type` aliases, PEP 695 generic
function syntax, and `typing.TypeIs`. Type aliases use `typing.TypeAlias`, and
generics use `typing.TypeVar` plus `typing.Generic`.

## Public API layer

`Query` is the FastAPI-native dependency object.

- `Query()` creates a loose-mode compiler.
- `Query(MyContract)` creates a strict-mode compiler.
- `Query.parse(...)` exists for tests and non-request code paths.
- `Query.__call__(request)` is what FastAPI uses through `Depends(query)`.

`Query` is generic over the selected backend output:

```python
mongo_query: Query[MongoQuery] = Query(ItemQuery)
sql_query: Query[SqlQuery] = Query(ItemQuery, emitter=SqlEmitter())
```

`CompiledQuery[T]` contains:

- `ast`: the backend-neutral AST
- `output`: the backend-specific query object

There is deliberately no `to(...)` or `to_mongo()` method. The backend is chosen
once when the dependency is created. This keeps FastAPI route code simple and
avoids redundant emitter work on the hot path.

## Contract typing model

`QueryContract` classes are declarative. They are inspected, not instantiated.
Annotations provide Python value types. `typing.Annotated[..., query_field(...)]`
provides Paramora metadata without assigning a metadata object to a typed class
attribute.

```python
class ItemQuery(QueryContract):
    active: bool
    status: Annotated[str, query_field("eq", "in")]
```

This avoids Pylance/Pyright assignment errors such as assigning `QueryFieldInfo`
to a field declared as `datetime` or `str`.

## Compiled contract layer

`compiled.py` converts public contract declarations into hot-path metadata once
when `Query(...)` is created. This layer precomputes:

- backend field names
- required fields
- sortable fields
- allowed operators
- scalar coercer functions
- list coercer functions

The parser therefore does not repeatedly inspect annotations or branch on field
types for every request.

## Parsing layer

`query_parser.py` normalizes request parameters, validates fields and operators,
coerces values, parses sorting, parses pagination, and returns a `QueryAst`.
This layer is backend-agnostic.

## AST layer

`query_ast.py` contains frozen dataclasses for filters, sort, pagination, and the
full query AST. The AST uses public contract field names. Backend aliases are
resolved by emitters using the compiled contract.

## Emission layer

`emitters/base.py` defines the generic `QueryEmitter[OutputT]` protocol. Emitters
consume a `QueryAst` plus `CompiledContract` and return a backend-specific object.

Built-in emitters:

- `MongoEmitter` → `MongoQuery`
- `SqlEmitter` → `SqlQuery`

The Mongo emitter returns PyMongo-compatible filter dictionaries and sort pairs.
The SQL emitter returns parameterized SQL fragments and a tuple of values.

## Error model

`errors.py` defines structured errors shaped similarly to FastAPI/Pydantic
validation errors. FastAPI integration maps `QueryValidationError` to HTTP 422.

## Validation and safety boundaries

Loose mode is less schema-strict, not raw-backend mode. The parser still rejects
raw backend operator syntax such as `$where`, `price__$gte`, and sort fields
containing `$`. This prevents common backend-operator injection paths while
keeping prototypes ergonomic.

For public endpoints, strict contracts are recommended.

## Profiling policy

Benchmarking should start with profiling, not speculation. Use
`benchmarks/profile_parse.py` to compare parser/emitter changes before adding
lower-level optimizations or considering non-Python internals.

Rust-backed internals may become useful later for real hotspots, but they should
not change public APIs. If native modules are added, typed Python wrappers or
`.pyi` stubs should preserve Pyright/Pylance support.
