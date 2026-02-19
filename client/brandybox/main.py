"""Entry point: auth, login or tray, sync loop."""

import logging
import os
import queue
import sys
from tkinter import Tk, Button, Frame, Toplevel, messagebox

import httpx

# Set when we fall back to xorg tray (no menu) because PyGObject is missing
_tray_fallback_xorg = False

# Prefer Wayland on Linux when available (must be set before any GUI/toolkit init).
# Qt (e.g. file dialogs, some tray backends) uses QT_QPA_PLATFORM; GTK uses GDK_BACKEND.
# Tk windows still run via XWayland when the session is Wayland (Tk has no native Wayland support).
if sys.platform == "linux":
    # Tray backend: if PyGObject (gi) is available, let pystray use AppIndicator (icon + menu).
    # If gi is missing (e.g. venv without system gobject), force xorg so the app still runs
    # (xorg has no context menu; we show a quick-access window instead).
    _have_gi = False
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        import gi.repository.Gtk  # noqa: F401
        _have_gi = True
    except (ImportError, ValueError, OSError, AttributeError):
        # AttributeError: frozen build may bundle a stub 'gi' without require_version
        pass
    if not _have_gi and os.environ.get("DISPLAY"):
        os.environ.setdefault("PYSTRAY_BACKEND", "xorg")
        globals()["_tray_fallback_xorg"] = True
    on_wayland = (
        os.environ.get("XDG_SESSION_TYPE") == "wayland"
        or os.environ.get("WAYLAND_DISPLAY")
    )
    if on_wayland:
        os.environ.setdefault("GDK_BACKEND", "wayland")
        os.environ.setdefault("QT_QPA_PLATFORM", "wayland")
    else:
        os.environ.setdefault("GDK_BACKEND", "x11")
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

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


def _show_quick_access_window(root: Tk, api: BrandyBoxAPI, schedule_ui) -> None:
    """Show a small window with Settings and Quit on Linux (xorg tray has no context menu)."""
    win = Toplevel(root)
    win.title("Brandy Box")
    win.resizable(False, False)
    win.attributes("-type", "dialog")
    f = Frame(win, padx=12, pady=12)
    f.pack(fill="both", expand=True)
    Button(f, text="Open Settings", width=14, command=lambda: schedule_ui(lambda: show_settings(api=api, parent=root))).pack(side="left", padx=(0, 8))
    Button(f, text="Quit", width=8, command=root.quit).pack(side="left")
    win.update_idletasks()
    # Position near top-right of screen
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    sw = root.winfo_screenwidth()
    win.geometry(f"+{sw - w - 24}+24")
    win.lift()


def _run_tray_with_ui(api: BrandyBoxAPI, access_token: str, creds: CredentialsStore) -> None:
    """Run tray in a background thread and tk mainloop on main thread so Settings works on Linux."""
    ui_queue: queue.Queue = queue.Queue()
    main_log = logging.getLogger("brandybox.main")

    root = Tk()
    # Keep root off-screen and minimal so Toplevel(Settings) can map on Linux when we deiconify briefly
    root.geometry("1x1+-10000+-10000")
    root.withdraw()

    def process_queue() -> None:
        try:
            while True:
                fn = ui_queue.get_nowait()
                main_log.info("Main: running scheduled UI task")
                try:
                    fn()
                except Exception:
                    main_log.exception("Error running UI task (e.g. opening Settings)")
        except queue.Empty:
            pass
        root.after(30, process_queue)  # poll every 30 ms so Settings opens quickly when tray is clicked

    schedule_ui = ui_queue.put

    run_tray(
        api,
        access_token,
        on_quit=root.quit,
        schedule_ui=schedule_ui,
        refresh_token_callback=lambda: creds.get_valid_access_token(api),
        settings_parent=root,
    )
    root.after(0, process_queue)  # start processing immediately so left-click → Settings works
    # If user has never set a sync folder, open Settings once so they see default ~/brandyBox (avoids broken tray menu on Linux)
    if not user_has_set_sync_folder():
        root.after(200, lambda: schedule_ui(lambda: show_settings(api=api, parent=root)))
    # xorg backend: no context menu; left-click still opens Settings (default action).
    # Use app menu "Quit Brandy Box" to quit. We no longer auto-show the quick-access window.
    root.mainloop()


def _ensure_cwd_repo_root() -> None:
    """Change process cwd to repo root so assets and file dialogs work when started from venv or desktop."""
    try:
        from brandybox.tray import _repo_assets_logo_dir
        assets_logo = _repo_assets_logo_dir()
        repo_root = assets_logo.parent.parent  # assets/logo -> assets -> repo root
        if repo_root.is_dir():
            os.chdir(repo_root)
    except Exception:
        pass


def main() -> None:
    """Run the Brandy Box desktop application."""
    _setup_logging()
    log = logging.getLogger("brandybox.main")
    log.info("Brandy Box starting")
    if _tray_fallback_xorg:
        log.info(
            "Tray: using xorg backend (no context menu). "
            "For full tray icon + menu, install PyGObject: sudo pacman -S python-gobject"
        )
    _ensure_cwd_repo_root()

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
