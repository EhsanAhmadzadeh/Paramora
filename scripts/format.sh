#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Formatting with Ruff"
uv run ruff format .

echo "==> Applying safe Ruff fixes"
uv run ruff check --fix .
