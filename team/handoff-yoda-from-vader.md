# Vader → Yoda — QA evidence (web SPA + backend telemetry)

**Date:** 2026-04-24  
**Scope:** New web frontend (`web/`), Google OAuth (admin-linked), preferences, client ping, admin diagnostics, Docker multi-stage, Tauri post-sync ping.

## Automated

- **Backend:** `cd backend && python -m pytest` — **58 passed** (includes `tests/test_web_features.py`: meta version, preferences, client ping, OAuth exchange, admin clients/events).
- **Tauri Rust:** `cd client-tauri/src-tauri && cargo test` — **passed** (after `client_ping` + `chrono`).
- **Web build:** `cd web && npm run build` — **passed** (TypeScript + Vite).
- **Docker:** `docker build -f backend/Dockerfile -t brandybox-test:local .` from repo root with **`.dockerignore`** — **succeeded** (image contains `/app/web_dist`).

## Security notes (must-fix if regressing)

- **OAuth:** Redirect URI must match `BRANDYBOX_PUBLIC_BASE_URL` + `/api/auth/google/callback`; register both tunnel and LAN URLs in Google Cloud if both are used. One-time `exchange` id expires in 2 minutes.
- **Admin routes:** `/api/admin/clients` and `/api/admin/events` require `is_admin`.
- **CORS:** Add every browser origin (comma-separated), e.g. `https://brandybox…,http://192.168.0.150:8081`, or browsers will block API calls.

## Exploratory (recommended follow-up)

- Mobile Safari: login, file upload size limits, safe-area with drawer.
- Google path end-to-end against a real Google Cloud project (not covered in CI).

## Open / none

No blocking defects recorded for merge from this pass.
