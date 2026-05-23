<div class="paramora-hero">
  <img src="assets/paramora-logo.png" alt="Paramora logo">
  <p><strong>Safe typed filtering for FastAPI.</strong></p>
</div>

# Paramora

Paramora turns user-controlled HTTP query parameters into safe, typed backend
query outputs for MongoDB, raw SQL, SQLAlchemy, SQLModel, and Mongo ODM
adapters.

Use it when you want FastAPI filtering APIs that are explicit, validated,
type-aware, documented, and safe by default.

```http
/items?price__gte=10&status__in=free,busy&sort=-created_at&limit=20
```

Paramora validates that request against your query contract, coerces values into
Python types, builds a small backend-neutral AST, and emits the backend output
you selected.

## Install

```bash
uv add paramora
```

Optional backend extras:

```bash
uv add "paramora[sqlalchemy]"
uv add "paramora[sqlmodel]"
uv add "paramora[postgres]"
uv add "paramora[odm]"
uv add "paramora[all]"
```

## Start here

- [Quickstart](quickstart.md): build your first FastAPI endpoint.
- [Usage guide](usage.md): learn the common patterns.
- [How-to guides](how-to.md): solve practical scenarios.
- [Query syntax](query-syntax.md): supported operators, sorting, and pagination.

## Backends

- [MongoDB](mongodb.md)
- [Raw SQL](sql.md)
- [SQLAlchemy and SQLModel](sqlalchemy.md)
- [Mongo ODM adapters](odms.md)

## Reliability

Paramora is tested with unit tests, FastAPI integration tests, SQLite execution
tests, mongomock-backed MongoDB tests, and optional PostgreSQL / SQLAlchemy /
SQLModel checks.

See [Testing](testing.md) and [Continuous Integration](ci.md).
