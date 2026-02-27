# install-brandybox-linux-client

Commands for **Garuda Linux** (or any Arch-based desktop): install and run the **Tauri client**, optionally add desktop menu entries. The Tauri client is the primary desktop app with modern UI, tray icon, and native integration.

---

## Agent behavior (execute autonomously)

When the user invokes this command, **perform the steps yourself**—do not only show instructions for copy-paste.

- **Default (no extra keyword):** Autonomously perform a **test-run**:
  1. From repo root: `cd client-tauri`, run `npm install`.
  2. Start the client: `npm run tauri dev` (or `npm run tauri:dev` if `tauri dev` fails). Run this in the **background** (it is a GUI/tray app and blocks otherwise). Use the workspace path for the repo root (e.g. `/home/markus/cursorProjects/brandyBox`).
  - Remind about prerequisites once: **Node.js** (LTS), **Rust** (`rustup default stable`), and for Arch/Garuda: `sudo pacman -S webkit2gtk gtk3 libappindicator-gtk3`.

- **If the user also says "install" (or "install for system", "menu entries", "install menu"):** In addition to the test-run setup, **install for the system** (menu entries):
  1. Build the Tauri app: `cd client-tauri && CARGO_TARGET_DIR="$(pwd)/src-tauri/target" npm run tauri:build` (ensures output lands in workspace for the install script).
  2. From repo root run: `chmod +x scripts/install_desktop_tauri.sh && ./scripts/install_desktop_tauri.sh`.
  - Tell the user that **Brandy Box**, **Brandy Box Settings**, and **Quit Brandy Box** are now in the application menu and they can enable "Start when I log in" in Settings.

Use the actual workspace path for the repo (e.g. `$WORKSPACE_PATH` or the path from context); do not assume `~/brandyBox` if the workspace is elsewhere.

---

## 1. Test-run the client (no install)

From your **repo root** (replace with your actual path, e.g. `/home/markus/cursorProjects/brandyBox`):

```bash
cd <repo_root>/client-tauri
npm install
npm run tauri dev
```

Or if `tauri dev` fails with CI/GTK issues: `npm run tauri:dev`

The tray icon should appear; use the menu to open Settings, sync, or Quit.

**Prerequisites** (Arch/Garuda):
- Node.js (LTS, e.g. 20.x) and npm
- Rust: <https://rustup.rs/> – `rustup default stable`
- `sudo pacman -S webkit2gtk gtk3 libappindicator-gtk3`

---

## 2. Install for the system (menu entries, recommended)

From **repo root** (after building the Tauri app):

```bash
cd <repo_root>/client-tauri
npm install
CARGO_TARGET_DIR="$(pwd)/src-tauri/target" npm run tauri:build
cd ..
chmod +x scripts/install_desktop_tauri.sh
./scripts/install_desktop_tauri.sh
```

This copies the AppImage to `~/.local/share/brandybox/` and adds **Brandy Box**, **Brandy Box Settings**, and **Quit Brandy Box** to the application menu. Start **Brandy Box** from the menu; in Settings you can enable "Start when I log in".

If the menu still shows an old icon: `kbuildsycoca5 --noincremental` (KDE).

---

## Summary

| Goal | Commands |
|------|----------|
| **Test-run** | Repo root → `cd client-tauri` → `npm install` → `npm run tauri dev` (run in background) |
| **Install (menu)** | Build: `cd client-tauri && npm run tauri:build` → `./scripts/install_desktop_tauri.sh` |

This command is available in chat as `/install-brandybox-linux-client`. Say **install** (or "install for system" / "menu entries") to also add desktop menu entries.
