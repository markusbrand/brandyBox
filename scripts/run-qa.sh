#!/usr/bin/env bash
# Run full QA: client-tauri tests, web build, backend pytest, mkdocs build.
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
echo "=== 2/4 Web (npm run build) ==="
(
  cd web
  if [ -f package-lock.json ]; then npm ci; else npm install; fi
  npm run build
)

echo ""
echo "=== 3/4 Backend (pytest) ==="
"$PYTHON" -m pytest backend -q

echo ""
echo "=== 4/4 Documentation (mkdocs build) ==="
"$PYTHON" -m mkdocs build

echo ""
echo "QA passed: client-tauri, web, backend, docs."
