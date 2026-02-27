---
name: quality-assurance-brandybox
description: Run quality checks, tests, and convention verification for the Brandy Box project. Focus on Tauri client, backend, and docs. Use when the user asks for QA, code review, testing, pre-merge checks, or validation of changes.
---

# Quality Assurance for Brandy Box

Apply this skill when performing QA, code review, or validating changes in the Brandy Box codebase.

**Focus:** The desktop client is the **Tauri + React** app (`client-tauri/`). QA validates Tauri client, backend, and docs. The Python client (`client/`) is deprecated and only relevant for legacy support.

## Project layout (conventions to verify)

- **Client (Tauri)**: `client-tauri/` — Desktop app: Rust core in `src-tauri/src/` (sync, api, config, credentials, network), React frontend in `src/` (App, Settings, Login). No global mutable state.
- **Backend**: `backend/app/` — `auth`, `users`, `files`, `db`. No global mutable state.
- **Tests**: Tauri unit tests in `client-tauri/src-tauri/` (`cargo test`). Backend tests under `backend/tests/` (pytest). E2E in `tests/e2e/` runs the **client-tauri** app.
- **Legacy**: `client/brandybox/` — Python client (deprecated); only verify when changes touch it.

## QA checklist

Use this checklist when reviewing or validating code:

- [ ] **Layout**: New client code in `client-tauri/` (Rust in `src-tauri/src/`, React in `src/`); backend in `backend/app/*`; no global mutable state.
- [ ] **Conventions**: Rust: clear module structure, doc comments on public items. React: components and hooks. Backend: cohesive classes, type hints and docstrings (Google or NumPy style) on public API.
- [ ] **Correctness**: Logic is correct; edge cases and errors (e.g. path traversal, missing files) are handled.
- [ ] **Security**: No obvious vulnerabilities (path traversal, injection, sensitive data exposure); auth and storage paths validated.
- [ ] **Tests**: New or changed behavior has tests; existing tests pass. Tauri changes: `cargo test` in `client-tauri/src-tauri`. Backend: pytest. Consider E2E for sync/UI flows.
- [ ] **Docs**: If Tauri client or backend code changed, docs are updated; run `mkdocs build` from repo root (output in `site/`).

## Commands (run from repo root)

**Full QA (one command):**
```bash
./scripts/run-qa.sh
```
Runs Tauri client tests, backend pytest, and `mkdocs build`. Uses `.venv` for Python when present; ensure `pytest` and `mkdocs` are installed (e.g. `pip install -r backend/requirements.txt mkdocs`).

**Individual steps:**
- **Tauri client**: `cd client-tauri/src-tauri && cargo test`
- **Backend**: `cd backend && pytest`
- **Documentation**: `mkdocs build` or `mkdocs serve`
- **E2E** (optional, builds and runs client-tauri app): `cd client-tauri && npm run tauri:build` then `python -m tests.e2e.run_all_e2e`

## Feedback format

When giving QA or code review feedback, use:

- **Critical**: Must fix before merge (bugs, security, broken tests).
- **Suggestion**: Should fix for consistency or maintainability (style, missing types/docs).
- **Nice to have**: Optional improvement.

## Git note

When suggesting commits: type the commit message in the Message field before clicking Commit, or use `git commit -m "message"` in the terminal to avoid the Source Control UI hanging.

## Additional resources

- For security checks and test patterns, see [reference.md](reference.md).
