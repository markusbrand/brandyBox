# Brandy Box

Dropbox-like desktop app that syncs a local folder to a Raspberry Pi over Cloudflare tunnel or LAN. Per-user storage, admin user management, and secure credential storage.

## Architecture

- **Backend**: Python (FastAPI) in Docker on Raspberry Pi. Storage under `/mnt/shared_storage/brandyBox/<email>/`. JWT auth, user CRUD (admin), file list/upload/download.
- **Client**: Python desktop app (Windows, Linux, Mac) with system tray, sync engine, and keyring-backed login. Uses `https://brandybox.brandstaetter.rocks` via Cloudflare tunnel, or `http://192.168.0.150:8080` when on LAN **brandstaetter**.

## Backend (Raspberry Pi)

### Prerequisites

- Docker and Docker Compose on the Pi
- Cloudflare tunnel already pointing at the Pi (e.g. to port 8080)
- Host path `/mnt/shared_storage/brandyBox` for user data

### Environment

Create a `.env` in `backend/` (or export):

```bash
BRANDYBOX_JWT_SECRET=<long-random-secret>
BRANDYBOX_SMTP_HOST=smtp.example.com
BRANDYBOX_SMTP_PORT=587
BRANDYBOX_SMTP_USER=
BRANDYBOX_SMTP_PASSWORD=
BRANDYBOX_SMTP_FROM=brandybox@example.com
BRANDYBOX_ADMIN_EMAIL=admin@example.com
BRANDYBOX_ADMIN_INITIAL_PASSWORD=<initial-admin-password>
BRANDYBOX_CORS_ORIGINS=https://brandybox.brandstaetter.rocks
```

### Run

```bash
cd backend
docker compose up -d
```

API: `http://<pi-ip>:8080` (LAN) or via tunnel at `https://brandybox.brandstaetter.rocks`. Health: `GET /health`.

### First admin

Set `BRANDYBOX_ADMIN_EMAIL` and `BRANDYBOX_ADMIN_INITIAL_PASSWORD`; on first start the backend creates that user as admin. Admins can create/delete users (password is sent by email).

## Client (Desktop)

### Development

```bash
cd client
pip install -e .
# From repo root so assets are findable:
cd ..
python -m brandybox.main
```

### Build (installers)

1. Generate logos (optional): `python scripts/generate_logos.py`
2. Build: `pip install pyinstaller && pyinstaller client/brandybox.spec`
3. Output: `client/dist/BrandyBox/`. See [assets/installers/README_installers.md](assets/installers/README_installers.md) for Linux/Windows/macOS installer steps.

### Usage

- Run the app; log in with email and password (or use stored credentials).
- In Settings, choose a local folder to sync (warning: contents will be synced/replaced).
- Tray icon shows sync state: synced (green), syncing (amber), error (red). Menu: Open folder, Settings, Pause, Quit.
- Option “Start when I log in” in Settings (no admin required).

## Documentation

- [Installers](assets/installers/README_installers.md)
- Development docs: `pip install mkdocs && mkdocs serve` then open http://127.0.0.1:8000, or `mkdocs build` for `site/`

## Security

- No secrets in repo; backend uses env for JWT, SMTP, admin.
- Client stores only refresh token and email in OS keyring.
- Auth and file endpoints are rate-limited; path traversal is blocked; CORS is restricted.
