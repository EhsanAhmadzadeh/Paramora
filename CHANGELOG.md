# Changelog

All notable changes to Paramora are documented here.

Paramora follows semantic-versioning-style release notes while it is in alpha.
Until `1.0`, public APIs, error shapes, AST contracts, and emitter interfaces may
still change between minor releases. Breaking changes are called out explicitly.

## [0.3.0] - Unreleased

### Added

- Raw SQL backend support for SQLite and PostgreSQL-oriented DB-API workflows.
- `SqlEmitter`, `SqliteEmitter`, and `PostgresEmitter`.
- `SqlQuery` for parameterized SQL fragments.
- `SqlStatement` for simple generated `SELECT` statements.
- SQL placeholder styles:
  - `qmark` for SQLite-style `?` placeholders.
  - `format` for psycopg-style `%s` placeholders.
  - `numeric` for `:1`, `:2`, ... placeholders.
  - `dollar` for PostgreSQL-style `$1`, `$2`, ... placeholders.
- SQLite integration tests using the standard-library `sqlite3` module.
- PostgreSQL SQL-shape tests and an optional real PostgreSQL integration test
  controlled by `PARAMORA_POSTGRES_DSN`.
- Benchmark scenarios for MongoDB, SQL, loose mode, invalid validation paths,
  and emitter-only paths.
- Benchmark suite runner for comparing all supported scenarios.
- Benchmark comparison helper for detecting regressions between JSON results.
- Richer documentation for MongoDB, raw SQL, strict mode, loose mode, and common
  application scenarios.

### Changed

- `Query` is generic over the backend output type: `Query[MongoQuery]`,
  `Query[SqlQuery]`, or a custom emitter output.
- `CompiledQuery[T].output` is now the primary way to access backend output.
- Documentation now focuses on practical usage first, then architecture details.
- Development and benchmark documentation are uv-first.

### Security

- SQL values are emitted as bound parameters, never interpolated into SQL text.
- SQL identifiers are validated before interpolation and double-quoted by
  default.
- Loose SQL mode still rejects raw backend operator syntax and unsafe SQL
  identifiers.

### Testing

- Added stronger SQL emitter tests.
- Added SQLite execution tests for equality, list operators, range filters,
  boolean filters, sorting, pagination, and injection-style payloads.
- Kept MongoDB behavior covered by `mongomock` integration tests.
- Maintained strict type checking across package code, tests, and benchmarks.

## [0.2.0] - Previous alpha

### Added

- Contract-based strict mode with `QueryContract` and `query_field(...)`.
- FastAPI-native `Query(...)` dependency usage.
- Generic emitter protocol for backend-specific outputs.
- Python 3.10+ compatibility baseline.
- Strict Pyright coverage for package code and tests.

### Changed

- Moved away from dictionary-based field declarations toward annotation-based
  query contracts.
- Reworked backend output access around typed compiled queries.

## [0.1.0] - Initial alpha

### Added

- Initial typed query compiler for FastAPI query parameters.
- MongoDB emitter with `MongoQuery` output.
- Backend-neutral AST.
- Strict and loose mode semantics.
- Structured validation errors compatible with FastAPI `422` responses.
