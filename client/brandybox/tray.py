"""System tray icon and menu (pystray).

Linux (Wayland + KDE Plasma / Garuda): We draw a small RGB icon (22 px, circle + "B")
with no transparency so AppIndicator displays it correctly. PNGs and RGBA often
render as a solid block. XOrg backend (PYSTRAY_BACKEND=xorg) does not work on Wayland.
"""

import logging
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk

import pystray
from PIL import Image, ImageDraw, ImageFont

# On Linux with xorg backend: (1) the tray window can be 1x1 initially, producing a
# single-pixel icon; force a minimum 24x24 draw size. (2) xorg has no context menu;
# left-click runs the default action (Settings). We add a quick-access window on Linux.
if getattr(pystray.Icon, "__module__", "").endswith("_xorg"):
    try:
        _xorg = __import__(pystray.Icon.__module__, fromlist=["Icon"])
        _orig_assert = _xorg.Icon._assert_icon_data

        def _patched_assert_icon_data(self, width, height):
            # Force minimum 24x24 so we never draw a 1x1 (single-pixel) icon
            width = max(width, 24)
            height = max(height, 24)
            return _orig_assert(self, width, height)

        _xorg.Icon._assert_icon_data = _patched_assert_icon_data
    except Exception:
        pass

from brandybox.api.client import BrandyBoxAPI
from brandybox.config import get_base_url_mode, get_sync_folder_path, user_has_set_sync_folder
from brandybox.network import get_base_url
from brandybox.sync.engine import SyncEngine
from brandybox.ui.notify import notify_error
from brandybox.ui.settings import show_settings

log = logging.getLogger(__name__)

# Tray icon size: Linux trays (KDE Plasma on Wayland, etc.) often use ~22–24 px.
# Use 32 px so the xorg backend has enough detail when the tray resizes the window.
TRAY_ICON_SIZE_DEFAULT = 64
TRAY_ICON_SIZE_LINUX = 32


def _draw_fallback_icon(size: int, color: Tuple[int, int, int]) -> Image.Image:
    """Draw a proper tray icon in memory (rounded shape + B) so we never show a plain square.
    On Linux use a circle so the tray can't render it as a square; otherwise rounded rect.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margin = max(1, size // 8)
    outline_w = max(1, size // 12)
    if sys.platform == "linux":
        # Circle: impossible for the tray to show as a square
        d.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=color + (255,),
            outline=(255, 255, 255, 220),
            width=outline_w,
        )
    else:
        r = max(4, size // 3)  # very rounded so it doesn't look square when scaled
        d.rounded_rectangle(
            [margin, margin, size - margin, size - margin],
            radius=r,
            fill=color + (255,),
            outline=(255, 255, 255, 220),
            width=outline_w,
        )
    # "B" so it's recognizable (large so it survives scaling to ~22px)
    font = None
    try:
        font_size = max(8, int(size * 0.55))
        for path in (
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ):
            try:
                font = ImageFont.truetype(path, font_size)
                break
            except (OSError, TypeError):
                continue
        else:
            font = ImageFont.load_default()
    except Exception:
        font = None
    if font:
        text = "B"
        if hasattr(d, "textbbox"):
            bbox = d.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        else:
            tw, th = (size // 2, size // 3) if not hasattr(d, "textsize") else d.textsize(text, font=font)
        x = (size - tw) // 2
        y = (size - th) // 2 - (size // 20)
        d.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    # On Linux pystray saves the icon as PNG; AppIndicator often shows RGBA as a solid block.
    # Return RGB (no alpha) so the saved PNG is opaque and the shape is preserved.
    if sys.platform == "linux":
        bg = Image.new("RGB", (size, size), (38, 38, 38))  # dark grey, works on most trays
        bg.paste(img, (0, 0), img)
        return bg
    return img


def _load_icon(path: Path, size: int = 64, fallback_color: Tuple[int, int, int] = (70, 130, 180)) -> Image.Image:
    """Load PNG and resize, or draw a proper fallback icon (rounded B).
    On Linux, composite onto an opaque background so AppIndicator (and similar
    backends) don't render transparent PNGs as a solid square.
    """
    if path.exists():
        try:
            img = Image.open(path).convert("RGBA")
            out = img.resize((size, size), Image.Resampling.LANCZOS)
            if out.size != (size, size):
                return _draw_fallback_icon(size, fallback_color)
            if sys.platform == "linux":
                # AppIndicator often shows transparent PNGs as a solid square.
                # Composite onto opaque background so the shape is preserved.
                bg = Image.new("RGBA", (size, size), fallback_color + (255,))
                bg.paste(out, (0, 0), out)
                return bg
            return out
        except Exception as e:
            log.info("Tray icon load failed for %s: %s, using fallback", path, e)
    else:
        log.debug("Tray icon missing at %s, using fallback", path)
    return _draw_fallback_icon(size, fallback_color)


def _is_connection_error(err: Optional[str]) -> bool:
    """True if the error indicates the backend was unreachable (transient)."""
    if not err:
        return False
    lower = err.lower()
    return (
        "connect" in lower
        or "timeout" in lower
        or "refused" in lower
        or "unreachable" in lower
        or "connection refused" in lower
        or "timed out" in lower
        or "name or service not known" in lower
        or "network is unreachable" in lower
    )


def _repo_assets_logo_dir() -> Path:
    """Return directory containing tray icons. Prefer package-bundled assets so
    icons work when run from venv or any cwd; then PyInstaller bundle; then repo root.
    """
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "assets" / "logo"
    # 1) Package dir: brandybox/assets/logo (works for pip install -e and normal install)
    pkg_assets = Path(__file__).resolve().parent / "assets" / "logo"
    if pkg_assets.is_dir() and (pkg_assets / "icon_synced.png").exists():
        return pkg_assets
    # 2) Walk up from .../client/brandybox/tray.py to find repo root (has assets/logo)
    start = Path(__file__).resolve()
    for parent in start.parents:
        assets_logo = parent / "assets" / "logo"
        if assets_logo.is_dir():
            return assets_logo
    return start.parent.parent.parent / "assets" / "logo"


def _icon_path(name: str) -> Path:
    """Resolve path to a single icon file."""
    assets_logo = _repo_assets_logo_dir()
    path = assets_logo / name
    log.debug("Icon path %s -> %s (exists=%s)", name, path, path.exists())
    return path


class TrayApp:
    """
    Tray icon with status (synced / syncing / error), menu, and background sync.
    """

    def __init__(
        self,
        api: BrandyBoxAPI,
        access_token: str,
        on_quit: Optional[Callable[[], None]] = None,
        schedule_ui: Optional[Callable[[Callable[[], None]], None]] = None,
        refresh_token_callback: Optional[Callable[[], Optional[str]]] = None,
        settings_parent: Optional["tk.Tk"] = None,
        on_logout: Optional[Callable[[], None]] = None,
    ) -> None:
        self._api = api
        self._api.set_access_token(access_token)
        self._on_quit = on_quit
        self._schedule_ui = schedule_ui
        self._refresh_token = refresh_token_callback
        self._settings_parent = settings_parent
        self._on_logout = on_logout
        self._paused = False
        self._status = "synced"  # synced | syncing | error
        self._last_error: Optional[str] = None  # so user can see why sync failed (tooltip)
        self._last_notified_error: Optional[str] = None
        self._last_notified_time: float = 0
        self._icon: Optional[pystray.Icon] = None
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_sync = threading.Event()
        self._sync_now = threading.Event()

    def _get_icon_image(self) -> Image.Image:
        # On Linux use a smaller size so the tray (often 22–24 px) doesn't scale down and lose shape.
        # On Linux we always use the drawn icon (circle + B): PNGs often render as a solid square
        # with AppIndicator/Plasma, and compositing didn't help, so skip PNG there entirely.
        size = TRAY_ICON_SIZE_LINUX if sys.platform == "linux" else TRAY_ICON_SIZE_DEFAULT
        if self._status == "syncing":
            if sys.platform != "linux":
                path = _icon_path("icon_syncing.png")
                if path.exists():
                    return _load_icon(path, size, (255, 180, 80))
            return _draw_fallback_icon(size, (255, 180, 80))
        if self._status == "error":
            if sys.platform != "linux":
                path = _icon_path("icon_error.png")
                if path.exists():
                    return _load_icon(path, size, (220, 80, 80))
            return _draw_fallback_icon(size, (220, 80, 80))
        # synced
        if sys.platform != "linux":
            path = _icon_path("icon_synced.png")
            if path.exists():
                return _load_icon(path, size, (70, 130, 180))
        return _draw_fallback_icon(size, (70, 130, 180))

    def _update_icon(self) -> None:
        if self._icon:
            self._icon.icon = self._get_icon_image()
            # Show error in tooltip when red (X11 WM_NAME is Latin-1 only)
            if self._status == "error" and self._last_error:
                msg = (self._last_error[:80]).encode("ascii", errors="replace").decode("ascii")
                self._icon.title = f"Brandy Box - error: {msg}"
            else:
                self._icon.title = "Brandy Box"

    def _set_status(self, status: str) -> None:
        self._status = status
        self._update_icon()

    def _sync_loop(self) -> None:
        log.info("Sync loop started")
        while not self._stop_sync.is_set():
            if self._paused:
                self._stop_sync.wait(timeout=1)
                continue
            # Don't sync until the user has set a folder (e.g. closed Settings with default ~/brandyBox)
            if not user_has_set_sync_folder():
                log.debug("Waiting for sync folder to be set")
                self._stop_sync.wait(timeout=30)
                continue
            sync_path = get_sync_folder_path()
            if not sync_path.exists():
                sync_path.mkdir(parents=True, exist_ok=True)
                log.info("Created sync folder %s", sync_path)
            log.info("Starting sync cycle (folder=%s)", sync_path)
            self._set_status("syncing")
            self._last_error = None
            engine = SyncEngine(
                self._api,
                sync_path,
                on_status=lambda _: None,
            )
            err = engine.run()
            # If 401, try refreshing the access token and sync once more
            if err and "401" in err and self._refresh_token:
                log.warning("Sync got 401, attempting token refresh")
                new_token = self._refresh_token()
                if new_token:
                    self._api.set_access_token(new_token)
                    err = engine.run()
            if err:
                self._last_error = err
                self._set_status("error")
                log.error("Sync failed: %s", err)
                # Desktop notification, throttled to at most once per 2 min per error
                now = time.monotonic()
                if err != self._last_notified_error or (now - self._last_notified_time) >= 120:
                    notify_error("Brandy Box – Sync error", err)
                    self._last_notified_error = err
                    self._last_notified_time = now
                # When backend is temporarily unreachable, retry sooner and (in automatic mode) re-resolve base URL
                if _is_connection_error(err):
                    if get_base_url_mode() == "automatic":
                        new_url = get_base_url()
                        self._api.set_base_url(new_url)
                        log.info("Backend unreachable; refreshed base URL for next retry: %s", new_url)
                    retry_interval = 15
                    log.debug("Pausing %ds until next retry (connection error)", retry_interval)
                else:
                    retry_interval = 60
                    log.debug("Pausing %ds until next sync cycle", retry_interval)
            else:
                self._set_status("synced")
                self._last_notified_error = None  # allow notification for next error
                log.info("Sync cycle completed successfully")
                retry_interval = 60
                log.debug("Pausing %ds until next sync cycle", retry_interval)
            # Wait retry_interval seconds, or until "Sync now" or stop requested
            self._sync_now.clear()
            for _ in range(retry_interval):
                if self._stop_sync.wait(timeout=1):
                    break
                if self._sync_now.is_set():
                    log.debug("Sync now requested, starting cycle")
                    break

    def _open_folder(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        import subprocess
        path = get_sync_folder_path()
        if path.exists():
            if sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            elif sys.platform == "win32":
                subprocess.run(["explorer", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)

    def _open_settings(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Open Settings on the main (UI) thread to avoid Linux tray/menu glitches."""
        def open_() -> None:
            try:
                log.info("Opening Settings window")
                show_settings(
                    api=self._api,
                    parent=self._settings_parent,
                    on_logout=self._on_logout,
                )
                log.info("show_settings returned")
            except Exception:
                log.exception("Failed to open Settings window")
        if self._schedule_ui:
            log.info("Tray: scheduling Settings open (main thread will run it)")
            self._schedule_ui(open_)
        else:
            open_()

    def _sync_now_click(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Request an immediate sync cycle (wakes the sync thread from its wait)."""
        self._sync_now.set()
        log.info("Sync now requested from menu")

    def _toggle_pause(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._paused = not self._paused
        item.checked = self._paused
        log.info("Sync paused=%s", self._paused)

    def _quit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        log.info("Quit requested")
        self._stop_sync.set()
        if self._icon:
            self._icon.visible = False
            self._icon.stop()
        if self._on_quit:
            self._on_quit()

    def _run_icon(self) -> None:
        """Entry for the tray thread (blocks)."""
        self._icon.run()

    def run(self) -> None:
        """Build menu, start sync thread, run tray (blocking unless schedule_ui set)."""
        backend_name = pystray.Icon.__module__.split(".")[-1] if pystray.Icon.__module__ else "?"
        log.info("Tray starting (backend=%s)", backend_name)
        # default=True: left-click on icon runs this (Dropbox-style: one click opens Settings)
        menu = pystray.Menu(
            pystray.MenuItem("Settings", self._open_settings, default=True),
            pystray.MenuItem("Open folder", self._open_folder),
            pystray.MenuItem("Sync now", self._sync_now_click),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Pause sync", self._toggle_pause, checked=lambda item: self._paused),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )
        self._icon = pystray.Icon(
            "Brandy Box",
            self._get_icon_image(),
            "Brandy Box",
            menu,
        )
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        if self._schedule_ui is not None:
            thread = threading.Thread(target=self._run_icon, daemon=True)
            thread.start()
            return
        self._icon.run()


def run_tray(
    api: BrandyBoxAPI,
    access_token: str,
    on_quit: Optional[Callable[[], None]] = None,
    schedule_ui: Optional[Callable[[Callable[[], None]], None]] = None,
    refresh_token_callback: Optional[Callable[[], Optional[str]]] = None,
    settings_parent: Optional["tk.Tk"] = None,
    on_logout: Optional[Callable[[], None]] = None,
) -> None:
    """
    Create and run tray app. If schedule_ui is provided, the tray runs in a
    background thread and schedule_ui(fn) is used to run UI (e.g. Settings)
    on the main thread; callers must run a mainloop and process scheduled calls.
    refresh_token_callback() can return a new access token on 401 so sync retries.
    settings_parent: when set, Settings opens as a Toplevel so it can be reopened.
    on_logout: when set, Settings shows a "Log out" option; called after clearing credentials.
    """
    app = TrayApp(
        api,
        access_token,
        on_quit,
        schedule_ui,
        refresh_token_callback,
        settings_parent,
        on_logout,
    )
    app.run()
