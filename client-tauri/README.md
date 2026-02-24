# Brandy Box – Tauri + React Client

Moderner Desktop-Client auf Basis von **Tauri 2** und **React** mit Material Design. Ersetzt die Python/Tk-Oberfläche durch ein webbasiertes UI; Tray und System-Integration laufen über die Tauri/Rust-API (unter Linux nutzt Tauri die passenden AppIndicator-Schnittstellen für Wayland).

## Features (wie Python-Client)

- **Login** mit E-Mail/Passwort; Credentials im OS-Keyring (Secret Service / Keychain / Credential Manager)
- **Sync-Ordner** wählbar; automatischer oder manueller Server-URL-Modus (LAN/Cloudflare)
- **System-Tray**: Icon + Kontextmenü (Settings, Ordner öffnen, Sync now, Quit); Icon und Tooltip zeigen den Sync-Status (Syncing / Synced / Error)
- **Einstellungen**: Konto, Speicher, Passwort ändern, Abmelden; Autostart; Admin-Bereich (Benutzer anlegen/löschen)
- **Sync-Engine** in Rust: Liste lokal/remote, Diff, Löschungen propagieren, Download/Upload, Zustand in `sync_state.json`; **automatischer Hintergrund-Sync** alle 60 Sekunden (15 s Verzögerung nach Start), sofern Sync-Ordner gesetzt und eingeloggt
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
npm run tauri build
```

Ausgabe z. B. unter `src-tauri/target/release/bundle/` (Debian/AppImage/msi/dmg je nach Plattform).

## Konfiguration

Wie beim Python-Client:

- **Linux**: `~/.config/brandybox/config.json` (oder `$XDG_CONFIG_HOME/brandybox`)
- **Windows**: `%APPDATA%\BrandyBox\config.json`
- **macOS**: `~/Library/Application Support/` (bzw. XDG)

Inhalt u. a.: `sync_folder`, `autostart`, `base_url_mode`, `manual_base_url`. Die gleichen Keys wie der Python-Client; bei Migration von Python auf Tauri bleiben Einstellungen und Keyring-Credentials nutzbar (gleicher Service-Name „BrandyBox“).

## Linux / Wayland

Tauri nutzt unter Linux die systemeigenen Tray-APIs; es ist **kein** venv-basierter Workaround mehr nötig. Das Tray-Icon und das Kontextmenü funktionieren mit dem gebauten Tauri-Client out of the box (inkl. Wayland/KDE).

**Hinweis:** Beim Start kann eine Deprecation-Meldung erscheinen: `libayatana-appindicator is deprecated. Please use libayatana-appindicator-glib`. Sie stammt von der System-Tray-Bibliothek (libayatana-appindicator), die Tauri/tray-icon nutzt, ist harmlos und verschwindet, sobald Upstream auf libayatana-appindicator-glib umstellt.

## Projektstruktur

- **Frontend (React)**: `src/` – Login, Settings, Tray-Menü-Setup (Material UI)
- **Backend (Rust)**: `src-tauri/src/` – `config`, `api`, `credentials`, `network`, `sync`, Commands für Tauri
- **Tray**: Erstellung im Frontend über `@tauri-apps/api/tray` und `@tauri-apps/api/menu`; Aktionen rufen Tauri-Commands auf (z. B. `open_sync_folder`, `run_sync`, `quit_app`). Der Backend-Command `run_sync` setzt den Sync-Status (syncing/synced/error) und emittiert das Event `sync-status`; das Frontend aktualisiert Tray-Icon (icon_synced/syncing/error) und Tooltip/Title entsprechend.

## Lizenz

Wie das Hauptprojekt Brandy Box (Apache 2.0).
