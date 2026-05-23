#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

case "${1:-serve}" in
  serve)
    uv run mkdocs serve
    ;;
  build)
    uv run mkdocs build --strict
    ;;
  *)
    echo "Usage: scripts/docs.sh [serve|build]" >&2
    exit 2
    ;;
esac
