"""System tray icon and menu (pystray)."""

import threading
import time
from pathlib import Path
from typing import Callable, Optional

import pystray
from PIL import Image

import sys

from brandybox.api.client import BrandyBoxAPI
from brandybox.config import get_sync_folder_path
from brandybox.sync.engine import SyncEngine
from brandybox.ui.settings import show_login, show_settings


def _load_icon(path: Path, size: int = 64) -> Image.Image:
    """Load PNG and resize to size. Fallback to a simple colored square."""
    if path.exists():
        try:
            img = Image.open(path).convert("RGBA")
            return img.resize((size, size), Image.Resampling.LANCZOS)
        except OSError:
            pass
    # Fallback: simple square
    img = Image.new("RGBA", (size, size), (70, 130, 180, 255))
    return img


def _icon_path(name: str) -> Path:
    """Resolve icon path: PyInstaller bundle (sys._MEIPASS) or repo root."""
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return base / "assets" / "logo" / name


class TrayApp:
    """
    Tray icon with status (synced / syncing / error), menu, and background sync.
    """

    def __init__(
        self,
        api: BrandyBoxAPI,
        access_token: str,
        on_quit: Optional[Callable[[], None]] = None,
    ) -> None:
        self._api = api
        self._api.set_access_token(access_token)
        self._on_quit = on_quit
        self._paused = False
        self._status = "synced"  # synced | syncing | error
        self._icon: Optional[pystray.Icon] = None
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_sync = threading.Event()

    def _get_icon_image(self) -> Image.Image:
        if self._status == "syncing":
            return _load_icon(_icon_path("icon_syncing.png"))
        if self._status == "error":
            return _load_icon(_icon_path("icon_error.png"))
        return _load_icon(_icon_path("icon_synced.png"))

    def _update_icon(self) -> None:
        if self._icon:
            self._icon.icon = self._get_icon_image()

    def _set_status(self, status: str) -> None:
        self._status = status
        self._update_icon()

    def _sync_loop(self) -> None:
        while not self._stop_sync.is_set():
            if self._paused:
                self._stop_sync.wait(timeout=1)
                continue
            sync_path = get_sync_folder_path()
            if not sync_path or not sync_path.exists():
                self._stop_sync.wait(timeout=30)
                continue
            self._set_status("syncing")
            engine = SyncEngine(
                self._api,
                sync_path,
                on_status=lambda _: None,
            )
            err = engine.run()
            if err:
                self._set_status("error")
            else:
                self._set_status("synced")
            self._stop_sync.wait(timeout=60)

    def _open_folder(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        import subprocess
        import sys
        path = get_sync_folder_path()
        if path and path.exists():
            if sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            elif sys.platform == "win32":
                subprocess.run(["explorer", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)

    def _open_settings(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        show_settings()

    def _toggle_pause(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._paused = not self._paused
        item.checked = self._paused

    def _quit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._stop_sync.set()
        if self._icon:
            self._icon.visible = False
            self._icon.stop()
        if self._on_quit:
            self._on_quit()

    def run(self) -> None:
        """Build menu, start sync thread, run tray (blocking)."""
        menu = pystray.Menu(
            pystray.MenuItem("Open folder", self._open_folder, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings", self._open_settings),
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
        self._icon.run()


def run_tray(api: BrandyBoxAPI, access_token: str, on_quit: Optional[Callable[[], None]] = None) -> None:
    """Create and run tray app (blocking)."""
    app = TrayApp(api, access_token, on_quit)
    app.run()
