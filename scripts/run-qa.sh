#!/usr/bin/env bash
# Run full QA: client-tauri tests, backend pytest, mkdocs build.
# Run from repo root. Uses .venv for backend and docs when present.
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${REPO_ROOT}/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi

echo "=== 1/3 Client-tauri (cargo test) ==="
(cd client-tauri/src-tauri && cargo test)

echo ""
echo "=== 2/3 Backend (pytest) ==="
"$PYTHON" -m pytest backend -q

echo ""
echo "=== 3/3 Documentation (mkdocs build) ==="
"$PYTHON" -m mkdocs build

echo ""
echo "QA passed: client-tauri, backend, docs."
