# install-brandybox-linux-client

Commands for **Garuda Linux** (or any Arch-based desktop): test-run the client first, then install it for the system.

---

## 1. Test-run the client (no install)

From your repo clone:

```bash
cd /home/markus/cursorWS/brandyBox/client
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m brandybox.main
```

- Replace `/path/to/brandyBox` with your actual path (e.g. `~/cursorWS/brandybox/brandyBox`).
- The tray icon should appear; use the menu to open settings, sync, or quit.
- To leave the venv: `deactivate`.

Optional: install dev deps and run tests before trying the GUI:

```bash
pip install -e ".[dev]"
pytest
```

---

## 2. Install for the system (user-wide)

**Option A — User install (recommended, no root):**

```bash
cd /home/markus/cursorWS/brandyBox/client
pip install --user -e .
```

Then run from anywhere:

```bash
python -m brandybox.main
```

If `~/.local/bin` is not on your `PATH`, add to `~/.bashrc` or `~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Option B — Editable + console script (optional):**

To get a `brandybox` (or `brandybox-client`) command, add a script entry to `client/pyproject.toml` under `[project.scripts]`, e.g.:

```toml
[project.scripts]
brandybox = "brandybox.main:main"
```

Then:

```bash
cd /path/to/brandyBox/client
pip install --user -e .
brandybox
```

---

## Summary

| Goal              | Commands |
|-------------------|----------|
| **Test-run only** | `cd client` → `source .venv/bin/activate` → `pip install -e .` → `python -m brandybox.main` |
| **Install (user)**| `cd client` → `pip install --user -e .` → `python -m brandybox.main` (from anywhere) |

This command is available in chat as `/install-brandybox-linux-client`.
