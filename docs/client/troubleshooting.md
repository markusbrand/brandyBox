# Client troubleshooting

## Linux: tray shows square icon / no context menu (recurring with new installs)

**Symptom:** On Linux (e.g. Garuda, KDE) the tray icon appears as a **square** instead of the Brandy Box “B” icon, **right-click does not open a context menu** (or a circle/indicator appears), and sometimes a settings popup stays on screen.

**Cause:** This happens when the app is run as the **standalone PyInstaller binary** (e.g. from `~/.local/share/brandybox/BrandyBox` or a desktop entry that points to it). The bundled environment cannot use the system PyGObject (AppIndicator) correctly, so the app falls back to the XOrg tray backend, which has these limitations. This is a **known, recurring issue** with new client installs on Linux.

**Fix — use the venv-based install:**

1. **Prerequisites** (Arch/Garuda):  
   `sudo pacman -S python-gobject libappindicator-gtk3`
2. From the **repo root**:  
   `python -m venv .venv --system-site-packages`  
   `source .venv/bin/activate`  
   `cd client && pip install -e . && cd ..`
3. Install desktop entries that run the venv:  
   `./scripts/install_desktop_venv.sh`  
   or  
   `./assets/installers/linux_install.sh --venv`
4. Start **Brandy Box** from the application menu (the entry will now use `python -m brandybox.main` from the venv). The tray will show the correct icon and right-click menu.

See also the main [README](https://github.com/markusbrand/brandyBox/blob/master/README.md) section “Install on Linux” and [Installers](https://github.com/markusbrand/brandyBox/blob/master/assets/installers/README_installers.md) (Option A — Venv).

## System metadata files (`.directory`, `Thumbs.db`, etc.)

Files like `.directory` (KDE Dolphin), `Thumbs.db`, `Desktop.ini` (Windows), and `.DS_Store` (macOS) are created automatically by the OS or file manager to store view settings or thumbnails. **Brandy Box does not need them** for syncing your actual content.

The client **ignores** these names: they are never uploaded and never downloaded. So they no longer clutter the server or cause permission errors on other operating systems. If such a file was synced to the server in the past, it remains there but the client will not try to download it (and will not delete it from the server, so other clients can keep it if they want). The list of ignored basenames is fixed in the sync engine (see `SYNC_IGNORE_BASENAMES` in `sync/engine.py`).

## Sync: "Permission denied" when downloading another file

**Symptom:** Sync fails or logs a warning like:

```text
[ERROR] brandybox.sync.engine: Download <path>: [Errno 13] Permission denied: '...'
```

This can happen on **Windows** (e.g. work PCs without admin rights) when the client cannot write a file locally—e.g. read-only or blocked by policy.

**What the client does:** The sync engine treats such permission errors as non-fatal: it logs a **warning** and **skips** that file, and continues syncing all other files. The sync cycle completes successfully; only the affected file is not updated locally.

**What you can do:**

- **Nothing:** If you don’t need that file, ignore the warning; the rest of your data stays in sync.
- **Remove read-only (if allowed):** Right-click the file → Properties → uncheck “Read-only” → OK, then sync again.
- **Delete or rename locally:** If you don’t need the file, delete or rename it; the next sync will try again and, if still denied, skip it again.
