# Continuous Integration

Paramora uses CI as a release gate. The goal is simple: a contributor should be
able to run the same checks locally that GitHub runs before a change is merged.

## Supported Python versions

Paramora supports Python **3.10+**. CI runs the test suite on:

- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13
- Python 3.14

The quality job runs on Python 3.10 because it is the compatibility baseline.
That job checks formatting, linting, strict typing, and documentation builds.

## Local quality gate

Run the full local gate with:

```bash
scripts/check.sh
```

That command runs:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -vv
uv run mkdocs build --strict
```

## Coverage

CI writes a coverage XML report and uploads it to Codecov. The README coverage
badge is generated from Codecov, so it tracks the latest uploaded coverage for
`main` instead of a hard-coded percentage.

## Documentation deployment

Documentation is built with MkDocs Material and deployed with GitHub Pages from
`.github/workflows/pages.yml`. The Pages workflow builds the `site/` directory
and deploys that artifact. It does not deploy the repository README directly.
