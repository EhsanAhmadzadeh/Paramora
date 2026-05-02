# Python support policy

Paramora currently supports Python `3.10+`.

Python 3.10 is the compatibility baseline for runtime code, tests, and type
checking. This means contributors should write modern Python that is still valid
on Python 3.10. Newer Python versions are supported, but they must not introduce
syntax or runtime APIs that break Python 3.10 users.

## Supported versions

Paramora aims to support currently relevant Python versions starting at 3.10:

- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13
- Python 3.14 when available in local and CI environments

The package metadata declares:

```toml
requires-python = ">=3.10"
```

## Development rules

Use syntax and APIs that work on Python 3.10. These are allowed and encouraged:

```python
str | None
list[str]
dict[str, object]
typing.Annotated
typing.Literal
typing.Protocol
typing.TypedDict
typing.TypeAlias
@dataclass(slots=True)
```

Avoid Python-version-specific features that are newer than 3.10 in runtime code,
for example:

```python
from datetime import UTC       # Python 3.11+
from typing import Self        # Python 3.11+
type FieldType = str | type    # Python 3.12+
class Emitter[T]: ...          # Python 3.12+
from typing import TypeIs      # Python 3.13+
```

If a newer typing helper is genuinely useful, prefer `typing_extensions` only
when the added dependency is justified. Otherwise, keep the implementation simple
and Python 3.10-native.

## Tooling baseline

Ruff and Pyright target Python 3.10:

```toml
[tool.ruff]
target-version = "py310"

[tool.pyright]
pythonVersion = "3.10"
```

These settings are intentional. They prevent tooling from introducing or
accepting syntax that would fail for Python 3.10 users.

## Raising the minimum version

The minimum supported Python version may be raised over time as older versions
reach end-of-life and the Python ecosystem moves forward. A minimum-version bump
should be treated as a compatibility decision, documented in release notes, and
reflected in:

- `pyproject.toml`
- README
- this document
- CI matrix
- release notes / changelog

Until then, Paramora should remain fully usable on Python 3.10.
