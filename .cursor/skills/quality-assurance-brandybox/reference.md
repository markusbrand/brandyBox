# QA Reference — Brandy Box

Extended checklist and patterns for deeper QA passes. QA focuses on the **Tauri client** (`client-tauri/`) as the desktop app.

## Security checks

- **Path traversal**: User-supplied paths must be validated; reject `..` and absolute paths outside user base. Backend: `backend/app/files/storage.py`, `test_storage.py`. Tauri: validate in Rust sync/config before filesystem access.
- **Auth**: Endpoints that touch user data must verify identity (JWT/session); no cross-user access.
- **Secrets**: No credentials or API keys in code; use keyring (Tauri: `keyring` crate), settings/env.

## Test patterns

- **Tauri client**: `cargo test` in `client-tauri/src-tauri/`; unit tests for sync, api, config modules.
- **Backend**: `pytest`, `monkeypatch` for settings, `tmp_path` for filesystem. Example: `backend/tests/test_storage.py`.
- **E2E**: `tests/e2e/` runs the built **client-tauri** app; build first with `cd client-tauri && npm run tauri:build`, then `python -m tests.e2e.run_all_e2e`.

## Doc regeneration

After Tauri client or backend code changes: update relevant `.md` under `docs/`, then run `mkdocs build` or `mkdocs serve` from repo root.
