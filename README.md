# Brandy Box

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Dropbox-like desktop app that syncs a local folder to a Raspberry Pi over Cloudflare tunnel or LAN. Per-user storage, admin user management, and secure credential storage.

## Architecture

- **Backend**: Python (FastAPI) in Docker on Raspberry Pi. Storage under `/mnt/shared_storage/brandyBox/<email>/`. JWT auth, user CRUD (admin), file list/upload/download.
- **Client**: Python desktop app (Windows, Linux, Mac) with system tray, sync engine, and keyring-backed login. Uses `https://brandybox.brandstaetter.rocks` via Cloudflare tunnel, or `http://192.168.0.150:8081` when on LAN **brandstaetter**.

## Backend (Raspberry Pi)

### Install the service on the Pi

The backend image is published to [GitHub Container Registry (GHCR)](https://github.com/markusbrand/brandyBox/pkgs/container/brandybox-backend). You can run it with a single Docker command—no need to clone the repository.

1. **Prerequisites on the Pi**
   - Docker installed (e.g. `curl -fsSL https://get.docker.com | sh` then `sudo usermod -aG docker $USER`; log out and back in).
   - Your HDD/storage mounted so that `/mnt/shared_storage/brandyBox` exists (create it if needed: `sudo mkdir -p /mnt/shared_storage/brandyBox && sudo chown pi:pi /mnt/shared_storage/brandyBox` or your Pi user).
   - Cloudflare tunnel (or another way) pointing at the Pi, e.g. to port 8081.

2. **Create a config directory and `.env`** (no clone: download the example from the repo):
   ```bash
   mkdir -p ~/brandybox-backend && cd ~/brandybox-backend
   curl -sL https://raw.githubusercontent.com/markusbrand/brandyBox/master/backend/.env.example -o .env
   # Edit .env and set BRANDYBOX_JWT_SECRET, SMTP, admin, etc. (no quotes needed for values)
   ```
   Set at least: `BRANDYBOX_JWT_SECRET` (e.g. `openssl rand -hex 32`), SMTP vars, `BRANDYBOX_ADMIN_EMAIL`, `BRANDYBOX_ADMIN_INITIAL_PASSWORD`, and `BRANDYBOX_CORS_ORIGINS` (e.g. `https://brandybox.brandstaetter.rocks`). Bcrypt limits passwords to 72 bytes.

3. **Run the backend** (one Docker command):
   ```bash
   docker run -d \
     --name brandybox-backend \
     --restart unless-stopped \
     -p 8081:8080 \
     -v brandybox_data:/data \
     -v /mnt/shared_storage/brandyBox:/mnt/shared_storage/brandyBox \
     --env-file .env \
     ghcr.io/markusbrand/brandybox-backend:latest
   ```
   The service listens on **port 8081**. If the image is private, run `docker login ghcr.io` first (username: GitHub user, password: PAT with `read:packages`). To use port 8080 instead, change `-p 8081:8080` to `-p 8080:8080`.

4. **Check it's running**
   ```bash
   docker ps
   curl http://localhost:8081/health
   ```
   You should see `{"status":"ok"}`. From another machine use `http://<pi-ip>:8081/health`; via the tunnel, `https://brandybox.brandstaetter.rocks/health`.
   - If the container is **Exited** or curl fails, check logs: `docker logs brandybox-backend`. Common cause: missing `BRANDYBOX_JWT_SECRET` in `.env`.
   - If you get **"Empty reply from server"**, wait 10–15 seconds after starting (startup runs DB init and admin bootstrap), then try again.
   - **Updates:** `docker pull ghcr.io/markusbrand/brandybox-backend:latest`, then `docker stop brandybox-backend && docker rm brandybox-backend` and run the `docker run` command again (your `brandybox_data` volume and `.env` are preserved).

5. **Optional: Install from clone (build from source)**  
   If you prefer to build the image locally or use the webhook listener:
   ```bash
   git clone https://github.com/markusbrand/brandyBox.git
   cd brandyBox/backend
   cp .env.example .env
   # Edit .env, then:
   docker compose up -d --build
   ```
   To use the GHCR image from the clone instead of building: `docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d`.

6. **Optional: Automatic updates via GitHub webhook**  
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

User files are stored under `BRANDYBOX_STORAGE_BASE_PATH` (default `/mnt/shared_storage/brandyBox`). Each user gets a subfolder (e.g. `admin@example.com`). Ensure that path exists on the host and is writable by the container; the `docker run` command above (or `docker-compose.yml` when using the clone) mounts it into the container. If sync fails (red tray icon), check backend logs and ensure the mount is correct.

### First admin

On first start, the backend creates an admin user from `BRANDYBOX_ADMIN_EMAIL` and `BRANDYBOX_ADMIN_INITIAL_PASSWORD`. Use that account in the desktop client; admins can create and delete users (passwords are sent by email).

## Client (Desktop)

### Install (download pre-built)

1. Open **[Releases](https://github.com/markusbrand/brandyBox/releases)** and download the zip for your system:
   - **Windows:** `BrandyBox-<version>-Windows-x64.zip`
   - **Linux:** `BrandyBox-<version>-Linux-x64.zip`
   - **macOS:** `BrandyBox-<version>-macOS-arm64.zip` or `-macOS-x64.zip`
2. Unzip the file.
3. Run the app:
   - **Windows:** Double-click `BrandyBox.exe` in the unzipped folder.
   - **macOS:** Open the folder and run the app (or drag it to Applications).
   - **Linux:** Open a terminal in the unzipped folder and run `./BrandyBox`. To add a menu entry, see [Installers](assets/installers/README_installers.md#linux).

**Linux (Garuda/KDE):** If the tray icon appears as a square and right-click has no menu, use the [venv-based install](#linux-venv-install-optional-if-tray-is-broken) instead. See [Client troubleshooting](docs/client/troubleshooting.md) for more.

### Other install options

**Development** (run from source):

```bash
cd client
pip install -e .
# From repo root so assets are findable:
cd ..
python -m brandybox.main
```

#### Linux venv install (optional; if tray is broken)

On Linux (e.g. Garuda, KDE) the standalone binary may show a square tray icon and no context menu. For the correct icon and menu, use the venv install: prerequisites `sudo pacman -S python-gobject libappindicator-gtk3` (Arch/Garuda), then from repo root: `python -m venv .venv --system-site-packages`, `source .venv/bin/activate`, `cd client && pip install -e . && cd ..`, and `./assets/installers/linux_install.sh --venv`. Start from the app menu; enable "Start when I log in" in Settings. See [Client troubleshooting](docs/client/troubleshooting.md).

**Build from source** (create your own zip):  
Generate logos (optional): `python scripts/generate_logos.py`. Then `pip install pyinstaller && pyinstaller client/brandybox.spec`. Output: `dist/BrandyBox/`. See [Installers](assets/installers/README_installers.md) for Linux/Windows/macOS steps.

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

## License

Copyright 2026 Markus Brand.

This project is open source under the [Apache License 2.0](LICENSE). See [LICENSE](LICENSE) for the full text. You may use, modify, and distribute the software under the terms of that license, with attribution as described in [NOTICE](NOTICE).
