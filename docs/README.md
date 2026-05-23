# Paramora documentation

This directory is the source for the Paramora documentation site.

The rendered documentation is published at:

https://ehsanahmadzadeh.github.io/Paramora/

## Main pages

- [Home](index.md)
- [Quickstart](quickstart.md)
- [Usage guide](usage.md)
- [How-to guides](how-to.md)
- [Query contracts](contracts.md)
- [Query syntax](query-syntax.md)
- [Errors](errors.md)
- [MongoDB backend](mongodb.md)
- [Raw SQL backend](sql.md)
- [SQLAlchemy and SQLModel](sqlalchemy.md)
- [Mongo ODM adapters](odms.md)
- [Testing strategy](testing.md)
- [Continuous Integration](ci.md)
- [Development](development.md)
- [Benchmarking](benchmarking.md)

## Build locally

```bash
uv sync --group docs
scripts/docs.sh serve
scripts/docs.sh build
```

GitHub Pages is deployed from the MkDocs-generated `site/` artifact, not from
the repository README.
