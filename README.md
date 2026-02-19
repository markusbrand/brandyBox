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

3. **Create a `.env` file** in `backend/` with your secrets (copy from `backend/.env.example`; no quotes needed for values):
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env and set BRANDYBOX_JWT_SECRET, SMTP, admin, etc.
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
   - After **pulling updates**, rebuild so the new code and dependencies are used: `docker compose build --no-cache && docker compose up -d`. Then wait ~15 s before `curl …/health`.
   - If you get **"Empty reply from server"**, wait 10–15 seconds after `docker compose up` (startup runs DB init and admin bootstrap), then try `curl` again. If it still fails, run `docker compose logs` to see if the app is crashing on the first request.

6. **Optional: Use the image from GitHub Container Registry**  
   The backend image is built and published to [GitHub Container Registry](https://github.com/markusbrand/brandyBox/pkgs/container/brandybox-backend) on every push to `master`/`main` and on releases. To pull and run that image instead of building locally (same `.env` and `docker-compose.yml`):
   ```bash
   cd ~/brandyBox/backend
   docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
   ```
   Image: `ghcr.io/markusbrand/brandybox-backend:latest`. If the package is private, run `docker login ghcr.io` first (username: your GitHub user, password: a PAT with `read:packages`). To make the package public, open the package page on GitHub → Package settings → Change visibility.

7. **Optional: Automatic updates via GitHub webhook**  
   When GitHub Actions finishes building the backend image, a webhook can trigger an update on the Pi so the new image is pulled and the container restarted without manual SSH.

   - **On the Pi:** A small Flask app (`backend/webhook_listener.py`) listens for GitHub webhook POSTs (e.g. on port 9000). It verifies the request with `X-Hub-Signature-256` using a secret, and on successful `workflow_run` completion it runs `backend/update_brandybox.sh`, which runs `docker compose -f docker-compose.yml -f docker-compose.ghcr.yml pull && … up -d`.
   - **Secret:** Set `GITHUB_WEBHOOK_SECRET` in the environment when starting the webhook listener (e.g. in a systemd unit or a small `.env` that is not committed). Use the same value in GitHub: repo → **Settings** → **Webhooks** → **Add webhook** → Payload URL: `https://deploy.brandstaetter.rocks/webhook` (Cloudflare tunnel to the Pi listener on port 9000), Content type: `application/json`, Secret: your secret. Under “Which events would you like to trigger this webhook?” choose **Workflow runs** (or “Let me select… → Workflow runs). The listener only acts when `workflow_run` has `action: completed` and `conclusion: success`.
   - **Run the listener:** e.g. `cd ~/brandyBox/backend && GITHUB_WEBHOOK_SECRET='your-secret' python webhook_listener.py` (or run it under systemd/gunicorn). Expose port 9000 via a Cloudflare tunnel (e.g. to `https://deploy.brandstaetter.rocks/webhook`) so GitHub can reach it.
   - **Cron (optional):** To start the webhook listener after a reboot, add a cron job for the Pi user: run `crontab -e` and add:
     ```cron
     @reboot cd /home/pi/brandyBox/backend && nohup python3 webhook_listener.py >> webhook.log 2>&1 &
     ```
     The listener loads `GITHUB_WEBHOOK_SECRET` from `backend/.env`, so the secret does not need to be in the cron line. Log output is appended to `backend/webhook.log`. Alternatively, a cron job can run `update_brandybox.sh` periodically (e.g. daily) as a fallback if webhooks are not used.

   See [Backend overview](docs/backend/overview.md) for the script and listener layout.

### Storage on the Pi

User files are stored under `BRANDYBOX_STORAGE_BASE_PATH` (default `/mnt/shared_storage/brandyBox`). Each user gets a subfolder (e.g. `admin@example.com`). Ensure that path exists on the host and is writable by the container; `docker-compose.yml` mounts it into the container. If sync fails (red tray icon), check backend logs and ensure the mount is correct.

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

### Install on Linux (venv — recommended; avoids tray icon/menu issues)

On Linux (e.g. Garuda, KDE), **use the venv-based install** so the tray shows the correct icon and right-click menu. The standalone PyInstaller binary on Linux often shows a square icon, no context menu, and can show a persistent popup; this is a known, recurring issue with new installs — the venv install avoids it.

1. **Prerequisites** (Arch/Garuda):  
   `sudo pacman -S python-gobject libappindicator-gtk3`
2. **Create venv and install client** (from repo root):  
   `python -m venv .venv --system-site-packages`  
   Then `source .venv/bin/activate`, `cd client && pip install -e . && cd ..`
3. **Install desktop entries** (from repo root, venv can be activated or not):  
   `chmod +x scripts/install_desktop_venv.sh && ./scripts/install_desktop_venv.sh`  
   Or: `./assets/installers/linux_install.sh --venv`
4. Start **Brandy Box** from the app menu, then in **Settings** enable **“Start when I log in”**.

No sudo (except for the pacman packages). The autostart entry is written to `~/.config/autostart/brandybox.desktop` when you enable it in Settings.

See [Client troubleshooting](docs/client/troubleshooting.md) if you see a square tray icon or no context menu.

### Build (installers)

1. Generate logos (optional, from repo root): `python scripts/generate_logos.py`
2. Build: `pip install pyinstaller && pyinstaller client/brandybox.spec`
3. Output: `dist/BrandyBox/` (run the app with `dist/BrandyBox/BrandyBox`). See [assets/installers/README_installers.md](assets/installers/README_installers.md) for Linux/Windows/macOS installer steps. **On Linux**, the standalone binary often has tray issues (square icon, no menu); use the venv install above instead for the application menu.

   **Pre-built assets:** For each [GitHub Release](https://github.com/markusbrand/brandyBox/releases) (e.g. [v0.1.0](https://github.com/markusbrand/brandyBox/releases/tag/v0.1.0)), the CI builds the client and attaches `BrandyBox-<version>-Windows-x64.zip`, `BrandyBox-<version>-Linux-x64.zip`, and `BrandyBox-<version>-macOS-<arch>.zip` (arm64 or x64) as downloadable assets. Unzip and run the executable (or use the Linux install script on the unzipped folder).

### Usage

- Run the app; log in with email and password (or use stored credentials).
- **Default sync folder** is `~/brandyBox` (e.g. `/home/markus/brandyBox`). If it already exists, that folder is used. Sync does not run until you have confirmed a folder (open Settings once and close, or choose another folder).
- **404 on login**: If the client shows "404 Not Found" for `…/api/auth/login`, the backend URL may be wrong. Check that `curl https://brandybox.brandstaetter.rocks/health` returns `{"status":"ok"}`. If `/health` works but login still 404s, your Cloudflare Tunnel may be using a path prefix; set `BRANDYBOX_BASE_URL` (e.g. `https://brandybox.brandstaetter.rocks/backend`) and run the app again.
- **Open Settings**: If you have never set a sync folder, the Settings window opens automatically (showing default ~/brandyBox); close it or choose another folder so sync can start. You can also run **"Brandy Box Settings"** from your app menu (Linux install adds this desktop entry) or run `BrandyBox --settings` to open Settings without the tray. Left-clicking the tray icon is supposed to open Settings too, but on some Linux setups the tray menu is broken (grey circle); use "Brandy Box Settings" instead.
- **Quit the app**: Right-click tray icon → Quit (if the menu opens). If the tray menu is broken, run **"Quit Brandy Box"** from your app menu (Linux install adds this), or run `killall BrandyBox` in a terminal.
- **Tray icon / menu on Linux**: For the full tray (icon + right‑click menu), install PyGObject and AppIndicator: `sudo pacman -S python-gobject libappindicator-gtk3` (Arch/Garuda). The app then uses the AppIndicator backend. **On Garuda/KDE, use the venv-based install** (see “Install on Linux” above or `./assets/installers/linux_install.sh --venv`) so the menu runs `python -m brandybox.main` with the system `gi`; the standalone PyInstaller binary falls back to the XOrg backend (square icon, no context menu). If you use a venv, create it with `python -m venv .venv --system-site-packages` so the venv can use the system `gi` module.
- Tray icon shows sync state: synced (blue), syncing (amber), error (red). The icon is drawn as a rounded "B". If the icon turns **red**, hover over it to see the error in the tooltip (e.g. "401 Unauthorized" or "Upload test.txt: …"); fix the cause (token, network, or Pi storage) and the next sync will retry. Expired tokens are refreshed automatically.
- Option “Start when I log in” in Settings (no admin required).

## Documentation

- [Installers](assets/installers/README_installers.md)
- [E2E autonomous sync test](tests/e2e/README.md) – run `python -m tests.e2e.run_autonomous_sync` (requires test credentials and backend).
- Development docs: `pip install mkdocs && mkdocs serve` then open http://127.0.0.1:8000, or `mkdocs build` for `site/`

## Security

- **No secrets in repo**: Passwords, JWT secret, and SMTP credentials are never committed. Backend reads from environment (use `backend/.env` from `backend/.env.example`; `.env` is gitignored).
- **Safe to publish**: The repo can be made public on GitHub; no credentials or API keys are in source. E2E tests use env vars `BRANDYBOX_TEST_EMAIL` and `BRANDYBOX_TEST_PASSWORD` (set locally only).
- Client stores only refresh token and email in OS keyring.
- Auth and file endpoints are rate-limited; path traversal is blocked; CORS is restricted.
