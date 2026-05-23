#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Checking formatting"
uv run ruff format --check .

echo "==> Linting"
uv run ruff check .

echo "==> Type checking"
uv run pyright

echo "==> Running tests"
uv run pytest -vv

echo "==> Building documentation"
uv run mkdocs build --strict

echo "==> All local checks passed"
