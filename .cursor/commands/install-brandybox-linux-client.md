# install-brandybox-linux-client

Commands for **Garuda Linux** (or any Arch-based desktop): test-run the client, then install with desktop menu entries. **Use the venv-based install** so the tray shows the correct icon and right-click menu (the standalone PyInstaller binary on Linux often shows a square icon and no context menu).

---

## 1. Test-run the client (no install)

From your **repo root** (replace `~/brandyBox` with your actual path, e.g. `/home/markus/cursorProjects/brandyBox`):

```bash
cd ~/brandyBox
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
cd ~/brandyBox
# If you haven’t already: python -m venv .venv --system-site-packages && source .venv/bin/activate && cd client && pip install -e . && cd ..
chmod +x scripts/install_desktop_venv.sh
./scripts/install_desktop_venv.sh
```

Or use the installer script (same result):

```bash
./assets/installers/linux_install.sh --venv
```

This adds **Brandy Box**, **Brandy Box Settings**, and **Quit Brandy Box** to the application menu. Start **Brandy Box** from the menu; in Settings you can enable “Start when I log in”. No sudo (except for the pacman packages above).

If the menu still shows an old icon: `kbuildsycoca5 --noincremental` (KDE).

---

## 3. Optional: run from anywhere (no menu entries)

If you only want a `brandybox` command without desktop entries:

```bash
cd ~/brandyBox/client
pip install --user -e .
```

Then from anywhere: `python -m brandybox.main` (ensure `~/.local/bin` is on your `PATH` if you use a console script).

---

## Summary

| Goal | Commands |
|------|----------|
| **Test-run** | From repo root: `python -m venv .venv --system-site-packages` → `source .venv/bin/activate` → `cd client && pip install -e . && cd ..` → `python -m brandybox.main` |
| **Install (menu)** | From repo root: set up venv + client as above, then `./scripts/install_desktop_venv.sh` or `./assets/installers/linux_install.sh --venv` |
| **Run from anywhere** | `cd client` → `pip install --user -e .` → `python -m brandybox.main` from any directory |

This command is available in chat as `/install-brandybox-linux-client`.
