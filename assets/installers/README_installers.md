# Brandy Box installers

**Pre-built assets:** On every [GitHub Release](https://github.com/markusbrand/brandyBox/releases), the CI attaches `BrandyBox-<version>-Windows-x64.zip` and `BrandyBox-<version>-Linux-x64.zip`. Download the zip for your OS, unzip, then run the executable (Windows: `BrandyBox.exe`; Linux: run `./BrandyBox` or use the install script on the unzipped folder).

**Linux (Garuda/KDE):** New installs often see a square tray icon and no context menu when using the standalone binary. Use **Option A (venv)** below for the correct tray; see also [Client troubleshooting](../docs/client/troubleshooting.md#linux-tray-shows-square-icon--no-context-menu-recurring-with-new-installs).

Build the client locally (from repo root):

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

**Option B — Standalone binary (PyInstaller):**

```bash
chmod +x assets/installers/linux_install.sh
./assets/installers/linux_install.sh
# Or pass the build folder: ./assets/installers/linux_install.sh dist/BrandyBox
```

Installs to `~/.local/share/brandybox` and adds desktop entries. On Garuda/KDE the binary may show a square tray icon and no context menu (XOrg fallback); use Option A for the best experience. No sudo.

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
