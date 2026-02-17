"""Client configuration: sync folder path, base URL mode, autostart."""

import json
import os
import sys
from pathlib import Path
from typing import Optional

# Default remote base URL (Cloudflare); avoid importing network here to prevent circular import
DEFAULT_REMOTE_BASE_URL = "https://brandybox.brandstaetter.rocks"


def _config_dir() -> Path:
    """Platform-specific config directory (no admin)."""
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return Path(base) / "BrandyBox"
    if os.environ.get("XDG_CONFIG_HOME"):
        return Path(os.environ["XDG_CONFIG_HOME"]) / "brandybox"
    return Path.home() / ".config" / "brandybox"


def get_config_path() -> Path:
    """Path to config file (e.g. config.json or settings.ini)."""
    d = _config_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "config.json"


def get_instance_lock_path() -> Path:
    """Path to the single-instance lock file (per user)."""
    return _config_dir() / "instance.lock"


def get_sync_state_path() -> Path:
    """Path to file storing last-synced paths for bidirectional delete propagation."""
    d = _config_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "sync_state.json"


def clear_sync_state() -> None:
    """Clear persisted sync state so next sync treats server as source of truth (e.g. after folder change)."""
    get_sync_state_path().write_text('{"paths": []}', encoding="utf-8")


def get_default_sync_folder() -> Path:
    """Default sync folder: ~/brandyBox (e.g. /home/markus/brandyBox)."""
    return Path.home() / "brandyBox"


def user_has_set_sync_folder() -> bool:
    """True if the user has ever saved a sync folder (config exists and has sync_folder key)."""
    path = get_config_path()
    if not path.exists():
        return False
    try:
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        return bool(data.get("sync_folder"))
    except (json.JSONDecodeError, OSError):
        return False


def get_sync_folder_path() -> Path:
    """Return configured sync folder, or default ~/brandyBox if none set."""
    path = get_config_path()
    if not path.exists():
        return get_default_sync_folder()
    try:
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = data.get("sync_folder")
        return Path(raw).resolve() if raw else get_default_sync_folder()
    except (json.JSONDecodeError, OSError):
        return get_default_sync_folder()


def set_sync_folder_path(folder: Path) -> None:
    """Persist sync folder path."""
    path = get_config_path()
    data = {}
    if path.exists():
        try:
            import json
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    data["sync_folder"] = str(folder.resolve())
    path.write_text(__import__("json").dumps(data, indent=2), encoding="utf-8")


def get_autostart() -> bool:
    """Whether to start at user login."""
    path = get_config_path()
    if not path.exists():
        return False
    try:
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("autostart", False)
    except (json.JSONDecodeError, OSError):
        return False


def set_autostart(enabled: bool) -> None:
    """Persist autostart preference and apply platform startup entry."""
    path = get_config_path()
    data = {}
    if path.exists():
        try:
            import json
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    data["autostart"] = enabled
    path.write_text(__import__("json").dumps(data, indent=2), encoding="utf-8")
    _apply_autostart_platform(enabled)


def get_base_url_mode() -> str:
    """Return 'automatic' or 'manual'. Default is 'automatic'."""
    path = get_config_path()
    if not path.exists():
        return "automatic"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("base_url_mode", "automatic") or "automatic"
    except (json.JSONDecodeError, OSError):
        return "automatic"


def set_base_url_mode(mode: str) -> None:
    """Persist base URL mode: 'automatic' or 'manual'."""
    path = get_config_path()
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    data["base_url_mode"] = mode
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_manual_base_url() -> str:
    """Return the manually configured base URL when mode is 'manual'. Default is Cloudflare URL."""
    path = get_config_path()
    if not path.exists():
        return DEFAULT_REMOTE_BASE_URL
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return (data.get("manual_base_url") or "").strip() or DEFAULT_REMOTE_BASE_URL
    except (json.JSONDecodeError, OSError):
        return DEFAULT_REMOTE_BASE_URL


def set_manual_base_url(url: str) -> None:
    """Persist manual base URL (used when base_url_mode is 'manual')."""
    path = get_config_path()
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    data["manual_base_url"] = (url or "").strip()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_settings_window_geometry() -> Optional[str]:
    """Last saved settings window geometry (e.g. '500x560+100+200') or None."""
    path = get_config_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("settings_window_geometry")
    except (json.JSONDecodeError, OSError):
        return None


def set_settings_window_geometry(geometry: str) -> None:
    """Save settings window geometry for next time."""
    path = get_config_path()
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    data["settings_window_geometry"] = geometry
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _executable_command() -> list:
    """Command to run Brandy Box (for startup entry)."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "brandybox.main"]


def _apply_autostart_platform(enabled: bool) -> None:
    """Create or remove user-level startup entry (no admin)."""
    cmd = _executable_command()
    if os.name == "nt":
        _autostart_windows(enabled, cmd)
    elif sys.platform == "darwin":
        _autostart_macos(enabled, cmd)
    else:
        _autostart_linux(enabled, cmd)


def _autostart_windows(enabled: bool, cmd: list) -> None:
    startup = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    if not startup.exists():
        return
    lnk = startup / "BrandyBox.lnk"
    if enabled:
        try:
            import subprocess
            target = cmd[0]
            args = " ".join(cmd[1:]) if len(cmd) > 1 else ""
            # Create shortcut via PowerShell
            ps = f'$s = (New-Object -COM WScript.Shell).CreateShortcut("{lnk}"); $s.TargetPath = "{target}"; $s.Arguments = "{args}"; $s.Save()'
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0)
        except Exception:
            pass
    else:
        try:
            if lnk.exists():
                lnk.unlink()
        except OSError:
            pass


def _autostart_macos(enabled: bool, cmd: list) -> None:
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    plist = launch_agents / "rocks.brandstaetter.brandybox.plist"
    if enabled:
        args_xml = "\n".join(f"    <string>{a}</string>" for a in cmd)
        plist.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>rocks.brandstaetter.brandybox</string>
  <key>ProgramArguments</key>
  <array>
{args_xml}
  </array>
  <key>RunAtLoad</key>
  <true/>
</dict>
</plist>
""", encoding="utf-8")
    else:
        if plist.exists():
            plist.unlink(missing_ok=True)


def _autostart_linux(enabled: bool, cmd: list) -> None:
    autostart_dir = Path.home() / ".config" / "autostart"
    autostart_dir.mkdir(parents=True, exist_ok=True)
    desktop = autostart_dir / "brandybox.desktop"
    if enabled:
        desktop.write_text(f"""[Desktop Entry]
Type=Application
Name=Brandy Box
Exec={" ".join(cmd)}
X-GNOME-Autostart-enabled=true
""", encoding="utf-8")
    else:
        if desktop.exists():
            desktop.unlink(missing_ok=True)
