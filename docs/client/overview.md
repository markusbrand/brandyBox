# Client overview

Desktop app: system tray, sync, settings (folder, autostart), login with keyring. When you choose a sync folder and confirm the warning, all contents of that folder are deleted and sync state is reset; the next sync downloads everything from the server (server is source of truth), then uploads local additions and propagates local deletions to the server. Deleting a folder locally removes all its files on the server on the next sync and the server removes now-empty parent directories; the same applies when the server has fewer files (e.g. deleted elsewhere)—local files are removed and empty directories cleaned up. Sync state (last-synced paths) must have been saved by at least one successful full sync for deletion propagation to work.

## Layout

- `brandybox/main.py` – Entry: try stored credentials → tray, else login
- `brandybox/tray.py` – Pystray icon (synced/syncing/error), menu, background sync loop
- `brandybox/api/client.py` – HTTP client (login, refresh, list, upload, download, delete)
- `brandybox/auth/credentials.py` – Keyring store for email + refresh token
- `brandybox/sync/engine.py` – Sync order: propagate deletes both ways, download server→local, upload local→server
- `brandybox/network.py` – Base URL: LAN (brandstaetter) vs Cloudflare
- `brandybox/config.py` – Sync folder, autostart preference, platform startup entries, sync state
- `brandybox/ui/` – Login window, settings (folder picker, autostart), dialogs

## Logging

Logs are written to a file in the config directory (e.g. `~/.config/brandybox/brandybox.log` on Linux, `%APPDATA%\BrandyBox\brandybox.log` on Windows). INFO and above go to stderr when run from a terminal. Use the log file to see sync cycles, errors, folder selection, token refresh, and whether the app is using LAN or Cloudflare for the backend.

## Linux / KDE system tray

On Linux the tray icon is drawn at 32 px so it stays crisp when the panel uses ~22–24 px (e.g. KDE Plasma). If the icon appears as a plain blue square or a click-indicator circle jumps on the tray, the default backend (XOrg/AppIndicator) is still the one that shows the icon on KDE. Do **not** set `PYSTRAY_BACKEND=gtk` on KDE: the GTK backend uses Gtk.StatusIcon, which Plasma often does not display, so you may see no icon at all.

## Build

From repo root: `pyinstaller client/brandybox.spec`. Icons in `assets/logo/` (generate with `python scripts/generate_logos.py`).
