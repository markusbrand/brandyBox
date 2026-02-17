# Client overview

Desktop app: system tray, sync, settings (server URL, folder, autostart, change password, admin user management), login with keyring. Only one instance runs per user; a second start shows a message and exits (standalone Settings via `--settings` is allowed). When you choose a sync folder and confirm the warning, all contents of that folder are deleted and sync state is reset; the next sync downloads everything from the server (server is source of truth), then uploads local additions and propagates local deletions to the server. If the backend is temporarily unreachable, the client retries every 15 seconds (instead of the usual 60) and, in automatic URL mode, re-resolves the base URL so it can switch back to the LAN server when it becomes reachable again. Deleting a folder locally removes all its files on the server on the next sync and the server removes now-empty parent directories; the same applies when the server has fewer files (e.g. deleted elsewhere)—local files are removed and empty directories cleaned up. Sync state (last-synced paths) must have been saved by at least one successful full sync for deletion propagation to work.

## Layout

- `brandybox/main.py` – Entry: try stored credentials → tray, else login
- `brandybox/tray.py` – Pystray icon (synced/syncing/error), menu, background sync loop
- `brandybox/api/client.py` – HTTP client (login, refresh, list, upload, download, delete)
- `brandybox/auth/credentials.py` – Keyring store for email + refresh token
- `brandybox/sync/engine.py` – Sync order: propagate deletes both ways, download server→local, upload local→server
- `brandybox/network.py` – Base URL: automatic (local vs remote) or manual. Local when WiFi SSID is "brandstaetter" or when on Ethernet and the Raspberry Pi at `http://192.168.0.150:8081` is reachable; otherwise remote (Cloudflare `https://brandybox.brandstaetter.rocks`).
- `brandybox/config.py` – Sync folder, base URL mode and manual URL, autostart preference, platform startup entries, sync state, instance lock path
- `brandybox/ui/` – Login window, settings (server URL automatic/manual, folder picker, autostart, change password, admin: create/delete users), dialogs

## Logging

Logs are written to a file in the config directory (e.g. `~/.config/brandybox/brandybox.log` on Linux, `%APPDATA%\BrandyBox\brandybox.log` on Windows). INFO and above go to stderr when run from a terminal. Use the log file to see sync cycles, errors, folder selection, token refresh, and whether the app is using LAN or Cloudflare for the backend.

## Linux / KDE system tray

On Linux the tray icon is drawn at 32 px so it stays crisp when the panel uses ~22–24 px (e.g. KDE Plasma). If the icon appears as a plain blue square or a click-indicator circle jumps on the tray, the default backend (XOrg/AppIndicator) is still the one that shows the icon on KDE. Do **not** set `PYSTRAY_BACKEND=gtk` on KDE: the GTK backend uses Gtk.StatusIcon, which Plasma often does not display, so you may see no icon at all.

## Build

From repo root: `pyinstaller client/brandybox.spec`. Icons in `assets/logo/` (generate with `python scripts/generate_logos.py`).
