# Brandy Box installers

## Download and run (recommended)

1. Go to [Releases](https://github.com/markusbrand/brandyBox/releases) and download the zip for your system:
   - **Windows:** `BrandyBox-<version>-Windows-x64.zip` → unzip, double-click `BrandyBox.exe`
   - **Linux:** `BrandyBox-<version>-Linux-x64.zip` → unzip, run `./BrandyBox` from the folder (or [add a menu entry](#linux) below)
   - **macOS:** `BrandyBox-<version>-macOS-arm64.zip` or `-macOS-x64.zip` → unzip, run the app (or drag to Applications)

**Linux (Garuda/KDE):** If the tray icon is a square and right-click has no menu, use the [venv install](#linux) (Option A) below. See [Client troubleshooting](../docs/client/troubleshooting.md#linux-tray-shows-square-icon--no-context-menu-recurring-with-new-installs).

---

## Build from source

From repo root:

```bash
pip install pyinstaller
pyinstaller client/brandybox.spec
```

Output: `dist/BrandyBox/` with the executable and assets.

## Linux

**Option A — Venv (recommended on Garuda/KDE for proper tray icon + context menu):**

```bash
cd /path/to/brandyBox
python -m venv .venv --system-site-packages && source .venv/bin/activate
cd client && pip install -e . && cd ..
./assets/installers/linux_install.sh --venv
```

Use `--system-site-packages` so the venv can use the system PyGObject (e.g. `pacman -S python-gobject libappindicator-gtk3`). This installs desktop entries that run `python -m brandybox.main` from the repo venv; the tray then shows the correct icon and right-click menu.

**Option B — Standalone binary (add to menu):**

From the repo: run `./assets/installers/linux_install.sh` (default: installs `dist/BrandyBox`), or `./assets/installers/linux_install.sh /path/to/unzipped/BrandyBox` to install a downloaded release to `~/.local/share/brandybox` and add desktop entries (Brandy Box, Brandy Box Settings, Quit Brandy Box). If you only have the release zip (no repo), run `./BrandyBox` from the unzipped folder; to add a menu entry, clone the repo and run the script with the path to your unzipped folder. On Garuda/KDE the binary may show a square tray icon and no context menu (XOrg fallback); use Option A for the best experience. No sudo.

## Windows

1. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php).
2. Build the client with PyInstaller (see above).
3. Open `assets/installers/brandybox.iss` in Inno Setup or run:
   ```cmd
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" assets\installers\brandybox.iss
   ```
4. Installer is created at `dist/BrandyBox-Setup.exe`. Run it for per-user install (no admin).

## macOS

1. Build: `pyinstaller client/brandybox.spec` (on a Mac).
2. Create a .app bundle (e.g. with `py2app` or by wrapping the folder in a bundle structure).
3. Optionally create a DMG for distribution. Autostart at login is configured from the app Settings (Launch Agent in `~/Library/LaunchAgents/`).
