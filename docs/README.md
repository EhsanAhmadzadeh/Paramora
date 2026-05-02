# Paramora documentation

This directory contains the source documentation for Paramora.

Paramora is a FastAPI-native typed query compiler. It validates HTTP query
parameters, coerces values into Python types, builds a backend-neutral AST, and
emits backend-specific output such as MongoDB query objects or parameterized SQL
fragments.

## Start here

- [Usage guide](usage.md) — full practical guide with MongoDB, SQL, strict mode,
  loose mode, aliases, required fields, sorting, pagination, and errors.
- [Quickstart](quickstart.md) — smallest useful FastAPI examples.
- [Query contracts](contracts.md) — how to define typed query contracts.
- [Query syntax](query-syntax.md) — supported HTTP query parameters and operators.

## Backend guides

- [MongoDB backend](mongodb.md) — using `MongoQuery` with PyMongo-style
  collections.
- [SQL backend](sql.md) — using `SqlEmitter` and `SqlQuery` with DB-API-style
  drivers such as SQLite.

## Reliability and maintenance

- [Error handling](errors.md) — structured errors and FastAPI 422 payloads.
- [Testing strategy](testing.md) — unit, FastAPI, MongoDB, SQLite, typing, and
  benchmark coverage.
- [Benchmarking, profiling, and future Rust hotspots](profiling-and-rust.md) —
  how to measure parser/emitter performance.
- [Development with uv](development.md) — local setup and quality gates.
- [Python support policy](python-support.md) — supported Python versions.

## How the docs are organized

The README is intentionally short enough for GitHub and PyPI readers. The `docs/`
files are more detailed and should be updated whenever public behavior changes.
Runtime wheels do not need to install this directory; it is source documentation
for users and contributors.
