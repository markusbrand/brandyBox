# install-brandybox-windows-client

PowerShell commands for **Windows** (e.g. Lenovo laptop, no admin): run the client from Cursor for testing, then build a portable exe for any Windows machine.

Replace `C:\path\to\brandyBox` with your actual repo path (e.g. `C:\Users\mbrandstaetter\cursorWS\brandyBox` or your workspace path).

---

## 1. Test-run from Cursor (no install, no admin)

From the **repo root** in PowerShell (e.g. from Cursor’s terminal):

```powershell
cd C:\path\to\brandyBox\client
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
cd ..
python -m brandybox.main
```

- The `cd ..` and run from repo root so assets and config paths resolve correctly.
- If execution policy blocks the activate script: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` (once), or use `cmd` and `.\.venv\Scripts\activate.bat` then `python -m brandybox.main`.
- Tray icon should appear. To exit the venv: `deactivate`.

Optional — run tests first:

```powershell
pip install -e ".[dev]"
pytest
```

---

## 2. Create a ready-to-use exe (portable folder)

Build from the **repo root** (not `client/`). No admin required if Python and pip are user-installed.

```powershell
cd C:\path\to\brandyBox
pip install pyinstaller
pyinstaller client/brandybox.spec
```

**Output:** `dist\BrandyBox\` containing:
- `BrandyBox.exe` — run this to start the app
- DLLs and assets (e.g. `assets\logo\`) — keep the whole folder together

**To use on any Windows machine:** Copy the entire `dist\BrandyBox` folder (e.g. to a USB stick or shared drive). On the target PC, run `BrandyBox.exe` from inside that folder. No installer or admin needed; per-user config and logs go to `%APPDATA%\BrandyBox\`.

---

## 3. Optional: single installer exe (Inno Setup)

For one `.exe` installer that does per-user install (no admin):

1. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php) (default path).
2. Build the folder as above (`pyinstaller client/brandybox.spec`).
3. In PowerShell from repo root:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "C:\path\to\brandyBox\assets\installers\brandybox.iss"
```

- Installer is created at `dist\BrandyBox-Setup.exe`. Run it on any Windows machine for a per-user install (Start Menu shortcut, uninstaller).

---

## Summary

| Goal | PowerShell (from repo or client as noted) |
|------|------------------------------------------|
| **Test-run in Cursor** | `cd …\brandyBox\client` → `.\.venv\Scripts\Activate.ps1` → `pip install -e .` → `cd ..` → `python -m brandybox.main` |
| **Portable exe folder** | From repo root: `pip install pyinstaller` → `pyinstaller client/brandybox.spec` → use `dist\BrandyBox\BrandyBox.exe` (copy whole folder to target PC) |
| **Single installer exe** | After PyInstaller build, run Inno Setup: `ISCC.exe …\assets\installers\brandybox.iss` → `dist\BrandyBox-Setup.exe` |

This command is available in chat as `/install-brandybox-windows-client`.
