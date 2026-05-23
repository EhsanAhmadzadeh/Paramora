# Continuous Integration

Paramora treats the CI pipeline as part of the public quality contract. The goal
is that contributors can trust the package across supported Python versions,
backend emitters, type checking, documentation, and benchmark-oriented changes.

## Supported Python versions

Paramora supports Python **3.10 and newer**. The CI test matrix runs the test
suite on:

- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13
- Python 3.14

Python 3.10 is the compatibility baseline. Runtime code should not use syntax or
standard-library features that are unavailable on Python 3.10.

## Quality gates

The `quality` job runs once on Python 3.10 and checks:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run mkdocs build --strict
```

Keeping these checks in one job makes style, typing, and documentation failures
fast to diagnose.

## Test matrix

The `tests` job runs after the quality gate and executes:

```bash
uv run pytest -vv --cov-report=term-missing --cov-report=xml
```

The test environment installs the development dependency group, which includes
backend testing dependencies such as `mongomock`, `sqlalchemy`, `sqlmodel`,
`psycopg`, `beanie`, and `mongoengine`.

## Coverage

Each Python version produces a `coverage.xml` artifact. CI uploads coverage to
Codecov with a Python-version flag, for example `py3.10` or `py3.13`.

The README coverage badge points to the Codecov report for the repository. After
the first successful CI run on the default branch, the badge should begin showing
real coverage data.

## Optional integration tests

Some integration tests require external services or environment variables. For
example, the PostgreSQL execution test requires:

```bash
PARAMORA_POSTGRES_DSN=postgresql://user:password@localhost:5432/paramora
```

Tests that need unavailable services should skip with a clear reason rather than
failing unrelated pull requests.
