"""Entry point: auth, login or tray, sync loop."""

import logging
import os
import queue
import sys
from tkinter import Tk, messagebox

import httpx

# Prefer Wayland on Linux when available; fall back to X11 (must be set before any GUI init).
if sys.platform == "linux":
    if os.environ.get("XDG_SESSION_TYPE") == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
        os.environ.setdefault("GDK_BACKEND", "wayland")
    else:
        os.environ.setdefault("GDK_BACKEND", "x11")

from brandybox.api.client import BrandyBoxAPI
from brandybox.auth.credentials import CredentialsStore
from brandybox.config import get_config_path, get_instance_lock_path, user_has_set_sync_folder
from brandybox.tray import run_tray
from brandybox.ui.settings import show_login, show_settings

# Hold the lock file open for the process lifetime so the lock stays acquired.
_instance_lock_file = None


def _try_acquire_single_instance_lock() -> bool:
    """Acquire an exclusive lock so only one app instance runs per user. Returns True if acquired."""
    global _instance_lock_file
    path = get_instance_lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _instance_lock_file = open(path, "w", encoding="utf-8")
    except OSError:
        return False
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(_instance_lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(_instance_lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError):
        _instance_lock_file.close()
        _instance_lock_file = None
        return False
    return True


def _setup_logging() -> None:
    """Configure logging to a file in the config dir and to stderr (INFO level)."""
    log_dir = get_config_path().parent
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "brandybox.log"
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger("brandybox")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    root.addHandler(fh)
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    root.addHandler(ch)
    root.info("Logging to %s", log_file)


def _run_tray_with_ui(api: BrandyBoxAPI, access_token: str, creds: CredentialsStore) -> None:
    """Run tray in a background thread and tk mainloop on main thread so Settings works on Linux."""
    ui_queue: queue.Queue = queue.Queue()
    schedule_ui = ui_queue.put

    root = Tk()
    root.withdraw()

    def process_queue() -> None:
        try:
            while True:
                fn = ui_queue.get_nowait()
                fn()
        except queue.Empty:
            pass
        root.after(100, process_queue)

    run_tray(
        api,
        access_token,
        on_quit=root.quit,
        schedule_ui=schedule_ui,
        refresh_token_callback=lambda: creds.get_valid_access_token(api),
    )
    root.after(0, process_queue)  # start processing immediately so left-click → Settings works
    # If user has never set a sync folder, open Settings once so they see default ~/brandyBox (avoids broken tray menu on Linux)
    if not user_has_set_sync_folder():
        root.after(200, lambda: schedule_ui(lambda: show_settings(api=api)))
    root.mainloop()


def main() -> None:
    """Run the Brandy Box desktop application."""
    _setup_logging()
    log = logging.getLogger("brandybox.main")
    log.info("Brandy Box starting")

    # Standalone Settings window (e.g. "Brandy Box Settings" from app menu) – no tray, no login
    if "--settings" in sys.argv:
        log.info("Running in standalone settings mode")
        root = Tk()
        root.withdraw()
        show_settings()
        sys.exit(0)

    # Single instance per user: only one tray/sync process
    if not _try_acquire_single_instance_lock():
        log.warning("Another instance is already running; exiting.")
        root = Tk()
        root.withdraw()
        messagebox.showinfo(
            "Brandy Box",
            "Brandy Box is already running. Use the system tray icon to open Settings or quit.",
        )
        sys.exit(0)

    api = BrandyBoxAPI()
    creds = CredentialsStore()
    access_token = creds.get_valid_access_token(api)
    if access_token:
        log.info("Using stored credentials, starting tray")
        _run_tray_with_ui(api, access_token, creds)
        return
    log.info("No valid credentials, showing login")
    # No valid credentials: show login
    def on_success(email: str, password: str) -> None:
        try:
            data = api.login(email, password)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                log.warning("Login failed: 401 for %s", email)
                msg = "Invalid email or password."
                try:
                    detail = e.response.json().get("detail", msg)
                    msg = detail if isinstance(detail, str) else msg
                except Exception:
                    pass
                messagebox.showerror("Login failed", msg)
                show_login(on_success=on_success, on_cancel=lambda: None)
                return
            log.exception("Login HTTP error: %s", e)
            raise
        log.info("Login successful for %s", email)
        creds.set_stored(email, data["refresh_token"])
        _run_tray_with_ui(api, data["access_token"], creds)
    show_login(on_success=on_success, on_cancel=lambda: None)


if __name__ == "__main__":
    main()
