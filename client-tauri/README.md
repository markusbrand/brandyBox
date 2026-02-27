# Brandy Box – Tauri + React Client

**Primary desktop client** for Brandy Box. Modern UI on **Tauri 2** and **React** with Material Design. Tray and system integration via Tauri/Rust (on Linux, native AppIndicator for Wayland). Includes the robust sync engine (v2) with verified state, hash-based comparison, and proper handling of skipped transfers.

## Features (wie Python-Client)

- **Login** mit E-Mail/Passwort; Credentials im OS-Keyring (Secret Service / Keychain / Credential Manager)
- **Sync-Ordner** wählbar; automatischer oder manueller Server-URL-Modus (LAN/Cloudflare)
- **System-Tray**: Icon + Kontextmenü (Settings, Ordner öffnen, Sync now, Quit); Icon und Tooltip zeigen den Sync-Status (Syncing / Synced / Warning / Error)
- **Einstellungen**: Konto, Speicher, Passwort ändern, Abmelden; Autostart; Admin-Bereich (Benutzer anlegen/löschen)
- **Sync-Engine** in Rust (robust v2): Liste lokal/remote, Diff, Löschungen propagieren, Download/Upload; nur verifizierte Pfade in `sync_state.json`; Hash-Vergleich wo möglich; **automatischer Hintergrund-Sync** alle 60 Sekunden (15 s Verzögerung nach Start)
- **Single-Instance** pro Benutzer (Datei-Lock)

## Voraussetzungen

- **Node.js** (LTS, z. B. 20.x) und **npm**
- **Rust** (stable): <https://rustup.rs/> – `rustup default stable`
- Unter **Linux** ggf. zusätzliche Pakete (siehe [Tauri – Prerequisites](https://tauri.app/start/prerequisites/)), z. B.:
  - Arch/Garuda: `sudo pacman -S webkit2gtk gtk3 libappindicator-gtk3`

## Entwicklung

```bash
cd client-tauri
npm install
npm run tauri dev
```

Beim ersten Start erscheint ein Fenster (z. B. Login). Das Tray-Icon wird beim Start erzeugt; Linksklick öffnet das Menü, „Settings“ zeigt das Fenster.

## Build (Produktion)

```bash
cd client-tauri
npm install
npm run tauri:build
```

Use `tauri:build` when CI=1 causes `--ci` errors; otherwise `npm run tauri build`.

Ausgabe z. B. unter `src-tauri/target/release/bundle/` (Debian/AppImage/msi/dmg je nach Plattform).

## Konfiguration

Wie beim Python-Client:

- **Linux**: `~/.config/brandybox/config.json` (oder `$XDG_CONFIG_HOME/brandybox`)
- **Windows**: `%APPDATA%\BrandyBox\config.json`
- **macOS**: `~/Library/Application Support/` (bzw. XDG)

Inhalt u. a.: `sync_folder`, `autostart`, `base_url_mode`, `manual_base_url`. Die gleichen Keys wie der Python-Client; bei Migration von Python auf Tauri bleiben Einstellungen und Keyring-Credentials nutzbar (gleicher Service-Name „BrandyBox“).

## Linux / Wayland

Tauri nutzt unter Linux die systemeigenen Tray-APIs; es ist **kein** venv-basierter Workaround mehr nötig. Das Tray-Icon und das Kontextmenü funktionieren mit dem gebauten Tauri-Client out of the box (inkl. Wayland/KDE).

**Hinweis:** Beim Start können folgende Meldungen erscheinen; sie sind harmlos:
- `libayatana-appindicator is deprecated. Please use libayatana-appindicator-glib` – stammt von der System-Tray-Bibliothek (Tauri/tray-icon), verschwindet mit Upstream-Update.
- `Gtk-Message: Failed to load module "appmenu-gtk-module"` – optionales GTK-Modul für App-Menüleiste; fehlt oft unter Linux und hat keinen Einfluss auf Tray oder Fenster.

**Große Dateien (z. B. MP4):** Bei „request or response body error“ oder „error sending request“ prüfen: Client macht 3 Versuche mit Pause. Wenn alle fehlschlagen, auf dem **Server** (Raspberry Pi) bzw. Proxy Timeouts erhöhen (z. B. uvicorn mit `--timeout-keep-alive 300`, nginx `proxy_read_timeout` / `client_max_body_size`).

## Projektstruktur

- **Frontend (React)**: `src/` – Login, Settings, Tray-Menü-Setup (Material UI)
- **Backend (Rust)**: `src-tauri/src/` – `config`, `api`, `credentials`, `network`, `sync`, Commands für Tauri
- **Tray**: Erstellung im Frontend über `@tauri-apps/api/tray` und `@tauri-apps/api/menu`; Aktionen rufen Tauri-Commands auf (z. B. `open_sync_folder`, `run_sync`, `quit_app`). Der Backend-Command `run_sync` setzt den Sync-Status (syncing/synced/error) und emittiert das Event `sync-status`; das Frontend aktualisiert Tray-Icon (icon_synced/syncing/error) und Tooltip/Title entsprechend.

## Lizenz

Wie das Hauptprojekt Brandy Box (Apache 2.0).
