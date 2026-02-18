# QA Reference — Brandy Box

Extended checklist and patterns for deeper QA passes.

## Security checks

- **Path traversal**: User-supplied paths must be validated; reject `..` and absolute paths outside user base. See `backend/app/files/storage.py` and `test_storage.py` for patterns.
- **Auth**: Endpoints that touch user data must verify identity (JWT/session); no cross-user access.
- **Secrets**: No credentials or API keys in code; use keyring/settings/env.

## Test patterns (existing)

- Backend: `pytest`, `monkeypatch` for settings, `tmp_path` for filesystem. Example: `backend/tests/test_storage.py`.
- Client: `pytest` with `pythonpath = ["."]`, testpaths = `["tests"]` in `client/pyproject.toml`.

## Doc regeneration

After client or backend code changes: update relevant `.md` under `docs/` (or equivalent), then run `mkdocs build` or `mkdocs serve` from repo root.
