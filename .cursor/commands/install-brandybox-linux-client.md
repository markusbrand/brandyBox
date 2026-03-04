# install-brandybox-linux-client

Commands for **Garuda Linux** (or any Arch-based desktop): install and run the **Tauri client**, optionally add desktop menu entries. The Tauri client is the primary desktop app with modern UI, tray icon, and native integration.

---

## Agent behavior (execute autonomously)

When the user invokes this command, **perform the steps yourself**—do not only show instructions for copy-paste.

- **Default (no extra keyword):** Autonomously perform a **test-run**:
  1. **Install system deps (Arch/Garuda):** Run `./scripts/install_tauri_prereqs.sh` from repo root. This requires sudo (user must run in a terminal and enter password). If this fails in the agent (no terminal for sudo), remind the user to run it manually.
  2. **Start the client:** Prefer the **installed** build (tray works on Wayland). If `./scripts/run_brandybox_installed.sh` exists and runs successfully, use that in the background. Otherwise: `cd client-tauri`, `npm install`, then `npm run tauri:dev` in the background. Note: dev mode does NOT show the tray icon on Wayland; only the installed build does.
  3. Use the workspace path for the repo root (e.g. `/home/markus/cursorProjects/brandyBox`).
  - Other prerequisites: **Node.js** (LTS), **Rust** (`rustup default stable`).

- **If the user says "dev" (or "development", "develop"):** Start in **dev mode** for immediate code changes: `cd client-tauri`, `npm install`, `npm run tauri:dev` in the background. The window auto-shows (no tray on Wayland). Frontend hot-reloads; Rust changes recompile.

- **If the user also says "install" (or "install for system", "menu entries", "install menu"):** In addition to the test-run setup, **install for the system** (menu entries):
  1. Build the Tauri app: `cd client-tauri && CARGO_TARGET_DIR="$(pwd)/src-tauri/target" npm run tauri:build` (ensures output lands in workspace for the install script).
  2. From repo root run: `chmod +x scripts/install_desktop_tauri.sh && ./scripts/install_desktop_tauri.sh`.
  - Tell the user that **Brandy Box**, **Brandy Box Settings**, and **Quit Brandy Box** are now in the application menu and they can enable "Start when I log in" in Settings.

Use the actual workspace path for the repo (e.g. `$WORKSPACE_PATH` or the path from context); do not assume `~/brandyBox` if the workspace is elsewhere.

---

## 1. Test-run the client (no install)

**Preferred (tray works on Wayland):** Run the installed build:

```bash
cd <repo_root>
./scripts/run_brandybox_installed.sh
```

**For development (immediate code changes, hot reload):**

```bash
cd <repo_root>/client-tauri
npm install
npm run tauri dev
```

In dev mode the window auto-shows on startup (so you can work without the tray). Frontend changes hot-reload; Rust changes trigger a recompile. The tray icon does NOT appear on Wayland in dev mode.

**Prerequisites** (Arch/Garuda):
- Node.js (LTS, e.g. 20.x) and npm
- Rust: <https://rustup.rs/> – `rustup default stable`
- System deps: `./scripts/install_tauri_prereqs.sh` (installs webkit2gtk, gtk3, libappindicator-gtk3)

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
| **Test-run** | Repo root → `./scripts/run_brandybox_installed.sh` (or `npm run tauri dev` if not installed) |
| **Install (menu)** | Build: `cd client-tauri && npm run tauri:build` → `./scripts/install_desktop_tauri.sh` |

This command is available in chat as `/install-brandybox-linux-client`. Say **install** for menu entries, or **dev** for development mode with hot reload.
