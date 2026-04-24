# Security review notes (Brandy Box)

Living checklist for **Vader** / operators. Not a formal audit sign-off. Update when auth, storage, or client shell behaviour changes.

## Backend (FastAPI)

| Topic | Status / notes |
|--------|----------------|
| **Passwords** | Bcrypt; no plaintext in logs. |
| **JWT** | Access + refresh; secret from env (`BRANDYBOX_JWT_SECRET`). |
| **File paths** | `resolve_user_path` rejects `..` and unsafe segments; regression tests in `backend/tests/test_storage.py`, `backend/tests/test_files_routes_http_security.py`. |
| **Cross-user files** | JWT subject scopes all file APIs; isolation covered by HTTP tests. |
| **Upload size** | Quotas during stream; optional **`BRANDYBOX_MAX_SINGLE_UPLOAD_BYTES`** → HTTP **413**. |
| **Rate limits** | Applied on auth and file routes (`app/limiter.py`). |
| **CORS** | `BRANDYBOX_CORS_ORIGINS`; align with real tunnel/origins. |

## Desktop client (Tauri + React)

| Topic | Status / notes |
|--------|----------------|
| **Capabilities** | `client-tauri/src-tauri/capabilities/default.json` — review when adding plugins or commands. See [Tauri client](client/tauri.md) (*Security posture* section). |
| **IPC** | Only bundled UI invokes Rust commands; validate inputs on Rust side for new commands. |
| **Secrets** | Tokens in OS keyring; not in web localStorage for session. |

## Operations

- **TLS**: Terminate HTTPS at Cloudflare tunnel or reverse proxy; do not expose plain HTTP to the internet.
- **Pi / Docker**: Least-privilege volume mounts; keep `.env` out of images.

## References

- [ADR 006 — Sync & trust boundaries](adrs/006-sync-semantics-trust-boundaries.md)
- OWASP File Upload Cheat Sheet (size, path, content handling)
