# Backend overview

Python FastAPI service in Docker on Raspberry Pi.

## Layout

- `app/main.py` – FastAPI app, CORS, lifespan (DB init, admin bootstrap)
- `app/config.py` – Settings from env (`BRANDYBOX_*`)
- `app/auth/` – JWT create/decode, dependencies (get_current_user, get_current_admin)
- `app/users/` – User model, routes (login, refresh, me, admin create/delete), service (email)
- `app/files/` – Storage (safe path resolution), routes (list, upload, download)
- `app/db/` – SQLite async session, `init_db`

## API

- `POST /api/auth/login` – email, password → access + refresh token
- `POST /api/auth/refresh` – refresh token → new token pair
- `GET /api/users/me` – current user (Bearer)
- `GET/POST/DELETE /api/users` – admin list, create, delete
- `GET /api/files/list` – list files for user
- `POST /api/files/upload?path=...` – upload body
- `GET /api/files/download?path=...` – download file

## Security

- Passwords hashed with bcrypt; JWT for access/refresh.
- File paths sanitized (no `..`); user scope by email.
- Rate limits on login/refresh and file endpoints; CORS from config.
