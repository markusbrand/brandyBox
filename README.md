# Brandy Box

Dropbox-like desktop app that syncs a local folder to a Raspberry Pi over Cloudflare tunnel or LAN. Per-user storage, admin user management, and secure credential storage.

## Architecture

- **Backend**: Python (FastAPI) in Docker on Raspberry Pi. Storage under `/mnt/shared_storage/brandyBox/<email>/`. JWT auth, user CRUD (admin), file list/upload/download.
- **Client**: Python desktop app (Windows, Linux, Mac) with system tray, sync engine, and keyring-backed login. Uses `https://brandybox.brandstaetter.rocks` via Cloudflare tunnel, or `http://192.168.0.150:8081` when on LAN **brandstaetter**.

## Backend (Raspberry Pi)

### Install the service on the Pi

1. **Prerequisites on the Pi**
   - Docker and Docker Compose installed (e.g. `curl -fsSL https://get.docker.com | sh` then `sudo usermod -aG docker $USER`; log out and back in).
   - Your HDD/storage mounted so that `/mnt/shared_storage/brandyBox` exists (create it if needed: `sudo mkdir -p /mnt/shared_storage/brandyBox && sudo chown pi:pi /mnt/shared_storage/brandyBox` or your Pi user).
   - Cloudflare tunnel (or another way) pointing at the Pi, e.g. to port 8081.

2. **Get the code on the Pi**
   ```bash
   cd ~
   git clone https://github.com/markusbrand/brandyBox.git
   cd brandyBox/backend
   ```

3. **Create a `.env` file** in `backend/` with your secrets (no quotes needed for values):
   ```bash
   BRANDYBOX_JWT_SECRET=<generate-a-long-random-string>
   BRANDYBOX_SMTP_HOST=smtp.example.com
   BRANDYBOX_SMTP_PORT=587
   BRANDYBOX_SMTP_USER=your-smtp-user
   BRANDYBOX_SMTP_PASSWORD=your-smtp-password
   BRANDYBOX_SMTP_FROM=brandybox@yourdomain.com
   BRANDYBOX_ADMIN_EMAIL=admin@yourdomain.com
   BRANDYBOX_ADMIN_INITIAL_PASSWORD=<choose-initial-admin-password>
   BRANDYBOX_CORS_ORIGINS=https://brandybox.brandstaetter.rocks
   ```
   Bcrypt limits passwords to 72 bytes; longer values are truncated when hashed.
   Generate a secret with e.g. `openssl rand -hex 32`.

4. **Build and start the container** (run from `backend/` so Docker finds `docker-compose.yml` and `.env`)
   ```bash
   cd ~/brandyBox/backend
   docker compose up -d --build
   ```
   The first run builds the image; later runs start the existing image. The service listens on **port 8081** by default (to avoid conflicts with other apps on 8080) and restarts automatically after a reboot. To use 8080 instead, add `HOST_PORT=8080` to `backend/.env`.
   - If you see **“address already in use”**, add `HOST_PORT=8082` (or another free port) to `backend/.env`, run `docker compose down`, then `docker compose up -d` again. Point your Cloudflare tunnel and client at that port.

5. **Check it’s running**
   ```bash
   docker compose ps
   curl http://localhost:8081/health
   ```
   You should see `{"status":"ok"}`. From another machine on the LAN use `http://<pi-ip>:8081/health`. Via the tunnel, use `https://brandybox.brandstaetter.rocks/health`.
   - If the container is **Exited** or curl fails, check logs: `docker compose logs` or `docker logs brandybox-backend`. Common causes: missing `BRANDYBOX_JWT_SECRET` in `.env`, or (on older compose) wrong `BRANDYBOX_DB_PATH`. The DB must use the `/data` volume (default `/data/brandybox.db`); do not set `BRANDYBOX_DB_PATH` to a path outside the container.
   - If you get **"Empty reply from server"**, wait 10–15 seconds after `docker compose up` (startup runs DB init and admin bootstrap), then try `curl` again. If it still fails, run `docker compose logs` to see if the app is crashing on the first request.

### First admin

On first start, the backend creates an admin user from `BRANDYBOX_ADMIN_EMAIL` and `BRANDYBOX_ADMIN_INITIAL_PASSWORD`. Use that account in the desktop client; admins can create and delete users (passwords are sent by email).

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
