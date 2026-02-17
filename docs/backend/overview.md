# Backend overview

Python FastAPI service in Docker on Raspberry Pi.

## Layout

- `app/main.py` – FastAPI app, CORS, lifespan (DB init, admin bootstrap)
- `app/config.py` – Settings from env (`BRANDYBOX_*`)
- `app/auth/` – JWT create/decode, dependencies (get_current_user, get_current_admin)
- `app/users/` – User model, routes (login, refresh, me, admin create/delete), service (email)
- `app/files/` – Storage (safe path resolution), routes (list, upload, download, delete)
- `app/db/` – SQLite async session, `init_db`

## API

- `POST /api/auth/login` – email, password → access + refresh token
- `POST /api/auth/refresh` – refresh token → new token pair
- `GET /api/users/me` – current user (Bearer)
- `GET/POST/DELETE /api/users` – admin list, create, delete
- `GET /api/files/list` – list files for user
- `POST /api/files/upload?path=...` – upload body
- `GET /api/files/download?path=...` – download file
- `DELETE /api/files/delete?path=...` – delete file (for bidirectional sync)

## Logging

Logging is configured at startup from env: `BRANDYBOX_LOG_LEVEL` (default `INFO`; use `DEBUG` for more detail) and optional `BRANDYBOX_LOG_FILE` (path to a file; if unset, logs go to stderr only, which Docker captures). Logs include startup/shutdown, login and refresh success/failure (email only), file operations (list/upload/download/delete with user and path), admin actions, auth failures (missing/invalid token, user not found), and unhandled exceptions (with traceback).

## Security

- Passwords hashed with bcrypt; JWT for access/refresh.
- File paths sanitized (no `..`); user scope by email.
- Rate limits on login/refresh and file endpoints; CORS from config.
