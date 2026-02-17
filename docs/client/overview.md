# Client overview

Desktop app: system tray, sync, settings (folder, autostart), login with keyring.

## Layout

- `brandybox/main.py` – Entry: try stored credentials → tray, else login
- `brandybox/tray.py` – Pystray icon (synced/syncing/error), menu, background sync loop
- `brandybox/api/client.py` – HTTP client (login, refresh, list, upload, download)
- `brandybox/auth/credentials.py` – Keyring store for email + refresh token
- `brandybox/sync/engine.py` – List local/remote, diff, upload/download (newer wins)
- `brandybox/network.py` – Base URL: LAN (brandstaetter) vs Cloudflare
- `brandybox/config.py` – Sync folder, autostart preference, platform startup entries
- `brandybox/ui/` – Login window, settings (folder picker, autostart), dialogs

## Build

From repo root: `pyinstaller client/brandybox.spec`. Icons in `assets/logo/` (generate with `python scripts/generate_logos.py`).
