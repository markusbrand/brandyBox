# Brandy Box installers

Build the client first (from repo root):

```bash
pip install pyinstaller
pyinstaller client/brandybox.spec
```

Output: `dist/BrandyBox/` with the executable and assets.

## Linux

```bash
chmod +x assets/installers/linux_install.sh
./assets/installers/linux_install.sh
# Or pass the build folder: ./assets/installers/linux_install.sh dist/BrandyBox
```

Installs to `~/.local/share/brandybox` and adds desktop entries: **Brandy Box**, **Brandy Box Settings**, **Quit Brandy Box** (use the last to stop the app when the tray menu does not open). No sudo.

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
