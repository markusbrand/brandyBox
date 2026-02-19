# Backend overview

Python FastAPI service in Docker on Raspberry Pi.

## Layout

- `app/main.py` – FastAPI app, CORS, lifespan (DB init, admin bootstrap)
- `app/config.py` – Settings from env (`BRANDYBOX_*`)
- `app/auth/` – JWT create/decode, dependencies (get_current_user, get_current_admin)
- `app/users/` – User model, routes (login, refresh, me, change-password, admin create/delete), service (email)
- `app/files/` – Storage (safe path resolution), routes (list, upload, download, delete)
- `app/db/` – SQLite async session, `init_db`

## API

- `POST /api/auth/login` – email, password → access + refresh token
- `POST /api/auth/refresh` – refresh token → new token pair
- `POST /api/auth/change-password` – current_password, new_password (Bearer); change own password
- `GET /api/users/me` – current user (Bearer)
- `GET/POST/DELETE /api/users` – admin list, create, delete
- `GET /api/files/list` – list files for user
- `POST /api/files/upload?path=...` – upload body
- `GET /api/files/download?path=...` – download file
- `DELETE /api/files/delete?path=...` – delete file; after removing the file, empty parent directories are removed so folder deletions stay in sync

## Logging

Logging is configured at startup from env: `BRANDYBOX_LOG_LEVEL` (default `INFO`; use `DEBUG` for more detail) and optional `BRANDYBOX_LOG_FILE` (path to a file; if unset, logs go to stderr only, which Docker captures). Logs include startup/shutdown, login and refresh success/failure (email only), file operations (list/upload/download/delete with user and path), admin actions, auth failures (missing/invalid token, user not found), and unhandled exceptions (with traceback).

## Automatic updates (GitHub webhook)

On the Raspberry Pi, updates to the backend image can be applied automatically when GitHub Actions has finished building:

- **`webhook_listener.py`** – Small Flask app (port 9000) that receives GitHub webhook POSTs. Verifies `X-Hub-Signature-256` using `GITHUB_WEBHOOK_SECRET`. When a `workflow_run` event has `action: completed` and `conclusion: success`, it runs `update_brandybox.sh` in the background.
- **`update_brandybox.sh`** – Script in `backend/`. Changes into the backend directory and runs `docker compose -f docker-compose.yml -f docker-compose.ghcr.yml pull` then `up -d`, so the latest GHCR image is used and the container is recreated with existing `.env` and volumes.
- **Cron:** A cron job (e.g. `@reboot`) can start the webhook listener so it runs after a Pi reboot. Alternatively, cron can run `update_brandybox.sh` on a schedule (e.g. daily) as a fallback if webhooks are not configured.

Configure the webhook in GitHub (repo → Settings → Webhooks): Payload URL pointing to the listener (e.g. `https://deploy.brandstaetter.rocks/webhook` via Cloudflare tunnel to the Pi on port 9000), Content type `application/json`, Secret equal to `GITHUB_WEBHOOK_SECRET`, and trigger “Workflow runs”. Do not commit the secret; set it in the environment when starting the listener.

## Security

- Passwords hashed with bcrypt; JWT for access/refresh.
- File paths sanitized (no `..`); user scope by email.
- Rate limits on login/refresh and file endpoints; CORS from config.
