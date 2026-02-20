# install-brandybox-linux-client

Commands for **Garuda Linux** (or any Arch-based desktop): test-run the client, then install with desktop menu entries. **Use the venv-based install** so the tray shows the correct icon and right-click menu (the standalone PyInstaller binary on Linux often shows a square icon and no context menu).

---

## Agent behavior (execute autonomously)

When the user invokes this command, **perform the steps yourself**—do not only show instructions for copy-paste.

- **Default (no extra keyword):** Autonomously perform a **test-run**:
  1. From repo root: ensure `.venv` exists with `python -m venv .venv --system-site-packages` (skip if `.venv` already exists).
  2. Install the client in the venv: `source .venv/bin/activate && cd client && pip install -e . && cd ..` (from repo root).
  3. Start the client: `python -m brandybox.main` from repo root with the venv activated. Run this in the **background** (it is a GUI/tray app and blocks otherwise). Use the workspace path for the repo root (e.g. `/home/markus/cursorProjects/brandyBox`).
  - If the user has not installed prerequisites, remind them once: `sudo pacman -S python-gobject libappindicator-gtk3` (Arch/Garuda).

- **If the user also says "install" (or "install for system", "menu entries", "install menu"):** In addition to the test-run setup, **install for the system** (menu entries):
  1. Ensure venv + client are set up as above (step 1–2).
  2. From repo root run: `chmod +x scripts/install_desktop_venv.sh && ./scripts/install_desktop_venv.sh` (or `./assets/installers/linux_install.sh --venv`).
  - Tell the user that **Brandy Box**, **Brandy Box Settings**, and **Quit Brandy Box** are now in the application menu and they can enable "Start when I log in" in Settings.

Use the actual workspace path for the repo (e.g. `$WORKSPACE_PATH` or the path from context); do not assume `~/brandyBox` if the workspace is elsewhere.

---

## 1. Test-run the client (no install)

From your **repo root** (replace with your actual path, e.g. `/home/markus/cursorProjects/brandyBox`):

```bash
cd <repo_root>
python -m venv .venv --system-site-packages
source .venv/bin/activate
cd client && pip install -e . && cd ..
python -m brandybox.main
```

- Use `--system-site-packages` so the venv can use the system PyGObject (needed for tray icon + menu).
- The tray icon should appear; use the menu to open Settings, sync, or Quit.
- To leave the venv: `deactivate`.

**Prerequisites** (Arch/Garuda, for full tray):  
`sudo pacman -S python-gobject libappindicator-gtk3`

Optional — run tests first:

```bash
pip install -e ".[dev]"
pytest
```

---

## 2. Install for the system (menu entries, recommended)

From **repo root** (venv and client already set up as in step 1):

```bash
cd <repo_root>
chmod +x scripts/install_desktop_venv.sh
./scripts/install_desktop_venv.sh
```

Or use the installer script (same result):

```bash
./assets/installers/linux_install.sh --venv
```

This adds **Brandy Box**, **Brandy Box Settings**, and **Quit Brandy Box** to the application menu. Start **Brandy Box** from the menu; in Settings you can enable "Start when I log in". No sudo (except for the pacman packages above).

If the menu still shows an old icon: `kbuildsycoca5 --noincremental` (KDE).

---

## 3. Optional: run from anywhere (no menu entries)

If you only want a `brandybox` command without desktop entries:

```bash
cd <repo_root>/client
pip install --user -e .
```

Then from anywhere: `python -m brandybox.main` (ensure `~/.local/bin` is on your `PATH` if you use a console script).

---

## Summary

| Goal | Commands |
|------|----------|
| **Test-run** | Repo root: `python -m venv .venv --system-site-packages` → `source .venv/bin/activate` → `cd client && pip install -e . && cd ..` → `python -m brandybox.main` (run in background) |
| **Install (menu)** | After test-run setup: `./scripts/install_desktop_venv.sh` or `./assets/installers/linux_install.sh --venv` |
| **Run from anywhere** | `cd client` → `pip install --user -e .` → `python -m brandybox.main` from any directory |

This command is available in chat as `/install-brandybox-linux-client`. Say **install** (or "install for system" / "menu entries") to also add desktop menu entries.
