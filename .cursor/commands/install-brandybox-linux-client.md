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
  1. **Always build first** so the installed app is current: `cd client-tauri && npm run tauri:build`.
  2. From repo root run: `chmod +x scripts/install_desktop_tauri.sh && ./scripts/install_desktop_tauri.sh`. The script installs the newest .deb and overwrites the installed binary with `target/release/brandybox` if it is newer (avoids stale client).
  3. **Start only from the installed path** (menu or `./scripts/run_brandybox_installed.sh`), not from `cargo run` or an old path, so the user sees the updated UI (e.g. version number in Settings).
  - Tell the user that **Brandy Box**, **Brandy Box Settings**, and **Quit Brandy Box** are now in the application menu and they can enable "Start when I log in" in Settings.

Use the actual workspace path for the repo (e.g. `$WORKSPACE_PATH` or the path from context); do not assume `~/brandyBox` if the workspace is elsewhere.

**Avoiding a stale client:** If the UI doesn’t show recent changes (e.g. version in Settings, server disk stats), the running app is likely an old build. Always **build** before **install**; the install script picks the newest .deb and overwrites the installed binary with `target/release/brandybox` when it’s newer. After install, **quit** any running Brandy Box and start again from the menu or `./scripts/run_brandybox_installed.sh`.

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

This copies the AppImage or .deb contents to `~/.local/share/brandybox/` and adds **Brandy Box**, **Brandy Box Settings**, and **Quit Brandy Box** to the application menu. The script uses the **newest** .deb (by mtime) and overwrites the installed binary with `target/release/brandybox` if it is newer, so the installed app is always current after a build. Start **Brandy Box** from the menu (or `./scripts/run_brandybox_installed.sh`); in Settings you can enable "Start when I log in".

If the menu still shows an old icon: `kbuildsycoca5 --noincremental` (KDE).

**If you still see an old UI** (e.g. no version in Settings, old storage labels): quit Brandy Box completely, then start it again from the menu or `./scripts/run_brandybox_installed.sh`. Do not start from `cargo run` or another path.

---

## Summary

| Goal | Commands |
|------|----------|
| **Test-run** | Repo root → `./scripts/run_brandybox_installed.sh` (or `npm run tauri dev` if not installed) |
| **Install (menu)** | Build: `cd client-tauri && npm run tauri:build` → `./scripts/install_desktop_tauri.sh` (always build first so installed app is current) |

This command is available in chat as `/install-brandybox-linux-client`. Say **install** for menu entries, or **dev** for development mode with hot reload.
