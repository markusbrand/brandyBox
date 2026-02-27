# Brandy Box – Tauri + React Client

**Primary desktop client** for Brandy Box. Modern UI on **Tauri 2** and **React** with Material Design. Tray and system integration via Tauri/Rust (on Linux, native AppIndicator for Wayland). Includes the robust sync engine (v2) with verified state, hash-based comparison, and proper handling of skipped transfers.

## Features (like Python client)

- **Login** with email/password; credentials in OS keyring (Secret Service / Keychain / Credential Manager)
- **Sync folder** selectable; automatic or manual server URL mode (LAN/Cloudflare)
- **System tray**: Icon + context menu (Settings, Open folder, Sync now, Quit); icon and tooltip show sync status (Syncing / Synced / Warning / Error)
- **Settings**: Account, storage, change password, logout; autostart; admin section (create/delete users)
- **Sync engine** in Rust (robust v2): List local/remote, diff, propagate deletes, download/upload; only verified paths in `sync_state.json`; hash comparison when available; **automatic background sync** every 60 seconds (15 s delay after start)
- **Single instance** per user (file lock)

## Prerequisites

- **Node.js** (LTS, e.g. 20.x) and **npm**
- **Rust** (stable): <https://rustup.rs/> – `rustup default stable`
- On **Linux** possibly extra packages (see [Tauri – Prerequisites](https://tauri.app/start/prerequisites/)), e.g.:
  - Arch/Garuda: `sudo pacman -S webkit2gtk gtk3 libappindicator-gtk3`

## Development

```bash
cd client-tauri
npm install
npm run tauri dev
```

On first start a window appears (e.g. Login). The tray icon is created on start; left-click opens the menu, "Settings" shows the window.

## Build (production)

```bash
cd client-tauri
npm install
npm run tauri:build
```

Use `tauri:build` when CI=1 causes `--ci` errors; otherwise `npm run tauri build`.

Output e.g. under `src-tauri/target/release/bundle/` (Debian/AppImage/msi/dmg depending on platform).

## Configuration

Same as Python client:

- **Linux**: `~/.config/brandybox/config.json` (or `$XDG_CONFIG_HOME/brandybox`)
- **Windows**: `%APPDATA%\BrandyBox\config.json`
- **macOS**: `~/Library/Application Support/` (or XDG)

Contents include: `sync_folder`, `autostart`, `base_url_mode`, `manual_base_url`. Same keys as Python client; when migrating from Python to Tauri, settings and keyring credentials remain usable (same service name "BrandyBox").

## Linux / Wayland

Tauri uses the native tray APIs on Linux; no venv-based workaround is needed. The tray icon and context menu work with the built Tauri client out of the box (including Wayland/KDE).

**Note:** On start, these messages may appear; they are harmless:
- `libayatana-appindicator is deprecated. Please use libayatana-appindicator-glib` – from the system tray library (Tauri/tray-icon), will disappear with upstream update.
- `Gtk-Message: Failed to load module "appmenu-gtk-module"` – optional GTK module for app menu bar; often missing on Linux and has no effect on tray or windows.

**Large files (e.g. MP4):** On "request or response body error" or "error sending request": client retries 3 times with delay. If all fail, increase timeouts on the **server** (Raspberry Pi) or proxy (e.g. uvicorn with `--timeout-keep-alive 300`, nginx `proxy_read_timeout` / `client_max_body_size`).

## Project structure

- **Frontend (React)**: `src/` – Login, Settings, tray menu setup (Material UI)
- **Backend (Rust)**: `src-tauri/src/` – `config`, `api`, `credentials`, `network`, `sync`, Tauri commands
- **Tray**: Created in frontend via `@tauri-apps/api/tray` and `@tauri-apps/api/menu`; actions invoke Tauri commands (e.g. `open_sync_folder`, `run_sync`, `quit_app`). Backend command `run_sync` sets sync status (syncing/synced/error) and emits `sync-status` event; frontend updates tray icon (icon_synced/syncing/error) and tooltip/title accordingly.

## License

Same as main Brandy Box project (Apache 2.0).
