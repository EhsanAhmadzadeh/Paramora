# Testing strategy

Paramora aims to be a reliable query compiler, so tests should cover behavior at
multiple levels.

## Test style

Tests use pytest and the AAA structure:

1. Arrange
2. Act
3. Assert

Each test should focus on one behavior. Use parametrization for value matrices
such as boolean parsing or supported operators.

## Test layers

- contract tests: annotation and metadata resolution
- coercion tests: scalar and enum conversion
- parser tests: query syntax, strict/loose behavior, pagination, sorting
- emitter tests: backend output shape
- FastAPI tests: dependency behavior and 422 responses
- mongomock tests: emitted Mongo queries executed against an in-memory collection
- SQLite tests: emitted SQL fragments executed against an in-memory SQLite database

## Coverage

The default pytest command runs coverage and reports missing lines. Coverage is a
signal, not a substitute for meaningful behavior tests.


## SQL integration tests

The SQL backend is tested with both exact emitter-output assertions and SQLite execution tests. The SQLite tests use only the Python standard library and verify that emitted `where`, `params`, `order_by`, `limit`, and `offset` values work together against a real SQL engine. They also include an injection-style payload test to ensure user values are bound as parameters rather than interpolated into SQL text.
