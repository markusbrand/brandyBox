# Client overview

**Primary client:** Tauri + React (`client-tauri/`) – see [Tauri client](tauri.md). **Fallback:** Python client (`client/`) – deprecated.

Desktop app: system tray, sync, settings (server URL, folder, autostart, change password, logout / switch account, admin user management), login with keyring. Only one instance runs per user; a second start shows a message and exits (standalone Settings via `--settings` is allowed). When a sync error occurs, a desktop notification is shown (Linux and macOS; throttled to at most once per 2 minutes for the same error). When a sync completes with downloads and/or uploads, a short "Sync complete" notification is shown (e.g. "5 file(s) downloaded from server" or "3 file(s) uploaded to server"), so you see when another device pushed changes (downloads) or when your local files were synced to the server (uploads). When you choose a sync folder and confirm the warning, all contents of that folder are deleted and sync state is reset; the next sync downloads everything from the server (server is source of truth), then uploads local additions and propagates local deletions to the server. If the backend is temporarily unreachable, the client retries every 15 seconds (instead of the usual 60) and, in automatic URL mode, re-resolves the base URL so it can switch back to the LAN server when it becomes reachable again. Deleting a folder locally removes all its files on the server on the next sync and the server removes now-empty parent directories; the same applies when the server has fewer files (e.g. deleted elsewhere)—local files are removed and empty directories cleaned up. Sync state (last-synced paths) must have been saved by at least one successful full sync for deletion propagation to work. If you close the app before a sync finishes, the next run picks up where you left off: state is saved after the delete phase and after each successful upload; completed downloads are recorded so the client does not re-download the same files. The backend stores a content hash (SHA-256) per file; when the server sends it, the client skips download when the local file already has the same hash.

## Layout

- `brandybox/main.py` – Entry: loop over stored credentials (or login); run tray; logout from Settings returns to login
- `brandybox/tray.py` – Pystray icon (synced/syncing/error), menu, background sync loop
- `brandybox/api/client.py` – HTTP client (login, refresh, list, upload, download, delete)
- `brandybox/auth/credentials.py` – Keyring store for email + refresh token
- `brandybox/sync/engine.py` – Sync order: propagate deletes both ways, download server→local, upload local→server; downloads and uploads run with multiple workers (default 8) and a rate limiter so the client stays under the backend’s 600 requests/minute while improving throughput on the local network.
- `brandybox/network.py` – Base URL: automatic (local vs remote) or manual. Local when WiFi SSID is "brandstaetter" or when on Ethernet and the Raspberry Pi at `http://192.168.0.150:8081` is reachable; otherwise remote (Cloudflare `https://brandybox.brandstaetter.rocks`).
- `brandybox/config.py` – Sync folder, base URL mode and manual URL, autostart preference, platform startup entries, sync state, instance lock path
- `brandybox/ui/` – Login window, settings (server URL automatic/manual, folder picker, autostart, **storage space** used/limit with progress bar, change password, logout / switch account, admin: create/delete users, **set per-user storage limit**), dialogs; UI follows Google Material–inspired guidelines (clear hierarchy, spacing, primary actions); `ui/notify.py` – desktop notifications for errors and for sync complete when files were downloaded or uploaded (Linux: notify-send with expire-time so popup auto-dismisses and stays in system notification history; macOS: osascript)

## Logging

Logs are written to a file in the config directory (e.g. `~/.config/brandybox/brandybox.log` on Linux, `%APPDATA%\BrandyBox\brandybox.log` on Windows). INFO and above go to stderr when run from a terminal. Use the log file to see sync cycles, errors, folder selection, token refresh, and whether the app is using LAN or Cloudflare for the backend.

## Linux display and tray

On Linux the app prefers **Wayland** when the session is Wayland (`XDG_SESSION_TYPE=wayland` or `WAYLAND_DISPLAY` set) and falls back to **X11** otherwise. Before any GUI init we set `QT_QPA_PLATFORM=wayland` (or `xcb` on X11) and `GDK_BACKEND=wayland` (or `x11`) so Qt and GTK components (e.g. file dialogs, some tray backends) use the native display. **Tk** (settings and login windows) has no native Wayland support and will run under XWayland when the session is Wayland; only a switch to another GUI toolkit (e.g. Qt) would allow those windows to be native Wayland.

## Linux / KDE system tray

On Linux the tray icon is drawn at 32 px so it stays crisp when the panel uses ~22–24 px (e.g. KDE Plasma). Error notifications use normal urgency and a 10 s expire-time so the popup disappears after a short time and the notification remains in the system notification history (tray); on KDE Plasma, critical-urgency notifications ignore expire-time and would stay on screen until dismissed. **For new installs on Linux (Garuda, KDE, etc.) use the venv-based install** so the app runs as `python -m brandybox.main` and can use the system PyGObject (AppIndicator). That gives the correct tray icon and right-click menu. The **standalone PyInstaller binary** on Linux often falls back to the XOrg backend (square icon, no context menu); this is a known, recurring issue — see [Client troubleshooting](troubleshooting.md#linux-tray-shows-square-icon-no-context-menu-recurring-with-new-installs). Do **not** set `PYSTRAY_BACKEND=gtk` on KDE: the GTK backend uses Gtk.StatusIcon, which Plasma often does not display, so you may see no icon at all.

See [Client troubleshooting](troubleshooting.md) for common issues (Linux tray, permission denied when syncing on Windows).

## Multiple devices

You can run the Brandy Box client on several machines at once (e.g. Windows laptop, Linux desktop, macOS) with the same account and sync folder. Each device has its own config and sync state (per user, per machine). **Last change wins:** if you delete a file on one client, the next sync deletes it on the server, and other clients then remove it locally on their next sync; if you edit a file, the version with the newer modification time (or matching content hash when available) is kept. There is no conflict merge — if two devices edit the same file offline, the one that syncs later overwrites the other.

## Sync performance

Sync uses **concurrent transfers** for downloads and uploads: up to 8 workers run in parallel so the client can use available bandwidth on the local network. A **rate limiter** caps how often new transfers start (10 per second) so the backend’s 600 requests/minute limit is not exceeded. Deletes still run sequentially (deepest first). If you see 429 (Too Many Requests), the client will retry after the indicated delay.

## Build

From repo root: `pyinstaller client/brandybox.spec`. Icons in `assets/logo/` (generate with `python scripts/generate_logos.py`).
