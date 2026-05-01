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

## Coverage

The default pytest command runs coverage and reports missing lines. Coverage is a
signal, not a substitute for meaningful behavior tests.
