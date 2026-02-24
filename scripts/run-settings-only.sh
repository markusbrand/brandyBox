#!/usr/bin/env bash
# Open Brandy Box Settings window only (no tray). Use when tray menu is broken (e.g. square icon).
# Run from repo root. Uses .venv if present.
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
if [ -x ".venv/bin/python" ]; then
  .venv/bin/python -m brandybox.main --settings
else
  echo "No .venv found. Create one with: python -m venv .venv --system-site-packages && source .venv/bin/activate && cd client && pip install -e . && cd .."
  exit 1
fi
