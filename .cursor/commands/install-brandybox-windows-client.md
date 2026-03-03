# install-brandybox-windows-client

PowerShell commands for **Windows** (e.g. Lenovo laptop, no admin): run the **Tauri + React** desktop client from Cursor for testing, then build an installer or portable exe for any Windows machine.

Uses the **client-tauri** UI (Material Design, system tray, Rust sync engine). Replace `C:\path\to\brandyBox` with your actual repo path (e.g. `C:\Users\mbrandstaetter\cursorWS\brandybox\brandyBox`).

---

## Prerequisites

- **Node.js** LTS (e.g. 20.x) and **npm**: <https://nodejs.org/>
- **Rust** (stable): <https://rustup.rs/> — run `rustup default stable`
- **Visual Studio Build Tools** (for Rust on Windows): typically needed for the `windows-sys` crate; install “Desktop development with C++” or the components suggested by `rustup`.

---

## 1. Test-run from Cursor (no install, no admin)

From the **repo root** in PowerShell (e.g. from Cursor’s terminal):

```powershell
cd C:\path\to\brandyBox\client-tauri
npm install
npm run tauri dev
```

- A window opens (e.g. Login); the **tray icon** appears in the system tray. Left-click the icon for the menu; “Settings” opens the window.
- Config and logs use the same paths as the old client: `%APPDATA%\BrandyBox\` (config, logs). Keyring credentials (service name “BrandyBox”) are compatible if you migrated from the Python client.

Optional — run frontend dev only (no Tauri window):

```powershell
npm run dev
```

---

## 2. Create a Windows build (installer or portable)

Build from **client-tauri** (no admin required):

```powershell
cd C:\path\to\brandyBox\client-tauri
npm install
npm run tauri:build
```

- Use `tauri:build` (script sets `CI=false`) to avoid CI-related build errors; otherwise you can run `npm run tauri build` if your environment is already set.
- **Output:** `src-tauri\target\release\bundle\`:
  - **MSI** installer (e.g. `Brandy Box_0.2.2_x64_en-US.msi`) — run on the target PC for a per-machine or per-user install.
  - Optionally **NSIS** or other formats if configured in `src-tauri/tauri.conf.json` under `bundle.targets` (e.g. add `"nsis"` for a single .exe installer).

**To use on any Windows machine:** Copy the built MSI (or the unpacked app from the bundle folder) to the target PC and run it. No admin needed for per-user install; config and logs go to `%APPDATA%\BrandyBox\`.

---

## 3. Optional: customize bundle targets (e.g. NSIS .exe)

For a single `.exe` installer (NSIS) in addition to or instead of MSI:

1. In `client-tauri/src-tauri/tauri.conf.json`, under `bundle.targets`, add `"nsis"` (e.g. `["msi", "nsis"]` for Windows).
2. Re-run from **client-tauri**:

```powershell
npm run tauri:build
```

- NSIS output appears in `src-tauri\target\release\bundle\nsis\` (e.g. `Brandy Box_0.2.2_x64-setup.exe`).

---

## Summary

| Goal | PowerShell (from repo or client-tauri as noted) |
|------|--------------------------------------------------|
| **Test-run in Cursor** | `cd …\brandyBox\client-tauri` → `npm install` → `npm run tauri dev` |
| **Windows build (MSI/portable)** | `cd …\brandyBox\client-tauri` → `npm install` → `npm run tauri:build` → use `src-tauri\target\release\bundle\` |
| **NSIS single .exe installer** | Add `"nsis"` to `bundle.targets` in `tauri.conf.json`, then `npm run tauri:build` → output in `bundle\nsis\` |

This command is available in chat as `/install-brandybox-windows-client`.
