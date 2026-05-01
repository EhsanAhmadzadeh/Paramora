# Paramora architecture

Paramora compiles FastAPI query parameters through a small, explicit pipeline:

```text
HTTP query params
→ Query / QueryContract
→ QueryParser
→ backend-neutral QueryAst
→ backend emitter
→ backend query object
```

The central rule is that Paramora never parses request parameters directly into
MongoDB dictionaries. Request syntax is parsed into a backend-neutral AST first.
Emitters are the only layer that knows how a backend represents filters, sort,
limit, and offset.

## Public API layer

`Query` is the FastAPI-native dependency object.

- `Query()` creates a loose-mode compiler.
- `Query(MyContract)` creates a strict-mode compiler.
- `Query.parse(...)` exists for tests and non-request code paths.
- `Query.__call__(request)` is what FastAPI uses through `Depends(query)`.

`QueryContract` classes are declarative. They are inspected, not instantiated.
Annotations provide Python value types. `typing.Annotated[..., query_field(...)]`
provides Paramora metadata without assigning a metadata object to a typed class
attribute.

## Contract typing model

Paramora deliberately uses this style:

```python
class ItemQuery(QueryContract):
    active: bool
    status: Annotated[str, query_field("eq", "in")]
```

Instead of this style:

```python
class ItemQuery(QueryContract):
    status: str = query_field("eq", "in")
```

The `Annotated` style avoids Pylance/Pyright assignment errors such as assigning
`QueryFieldInfo` to a field declared as `datetime` or `str`.

## Parsing layer

`query_parser.py` normalizes request parameters, validates fields and operators,
coerces values, parses sorting, parses pagination, and returns a `QueryAst`.

This layer is backend-agnostic.

## AST layer

`query_ast.py` contains frozen dataclasses for filters, sort, pagination, and the
full query AST. The AST uses public contract field names. Backend aliases are
resolved by emitters.

## Emission layer

`emitters/base.py` defines the generic `QueryEmitter[QueryOutputT]` protocol.
`CompiledQuery.to(...)` accepts any emitter implementing that protocol and
returns the backend-specific output type.

`emitters/mongo.py` turns `QueryAst` into `MongoQuery`.

The Mongo emitter:

- maps Paramora operators to Mongo operators
- merges range predicates on the same field
- applies backend aliases
- returns PyMongo-compatible sort pairs

## Error model

`errors.py` defines structured errors shaped similarly to FastAPI/Pydantic
validation errors. FastAPI integration maps `QueryValidationError` to HTTP 422.

## Validation and safety boundaries

Loose mode is intentionally less schema-strict, not raw-backend mode. The parser
still rejects raw backend operator syntax such as `$where`, `price__$gte`, and
sort fields containing `$`. This prevents common Mongo operator-injection paths
while keeping prototypes ergonomic.

`in` and `nin` require at least one comma-separated value. Empty list filters are
reported as structured validation errors instead of silently emitting surprising
backend queries.

## Generics and backend extension

The extension point for backend output is `QueryEmitter[OutputT]`. A backend
package can expose a typed emitter without changing Paramora's parser or AST:

```python
class MyEmitter(QueryEmitter[MyBackendQuery]):
    def emit(self, ast: QueryAst, fields: Mapping[str, QueryField]) -> MyBackendQuery:
        ...

compiled: CompiledQuery
backend_query = compiled.to(MyEmitter())  # inferred as MyBackendQuery
```

This keeps generics useful at the API boundary where developers choose a backend.
The core `Query` object remains backend-neutral.

## Profiling policy

Benchmarking should start with profiling, not speculation. Use
`benchmarks/profile_parse.py` to compare parser/emitter changes before adding
lower-level optimizations or considering non-Python internals.
