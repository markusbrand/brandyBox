"""Storage quota: server limit (config) and per-user usage/limits."""

import logging
import re
from pathlib import Path
from typing import Optional, Tuple

from app.config import get_settings
from app.files.storage import user_base_path

log = logging.getLogger(__name__)

# Optional: 1–3 digits, optional decimal, then unit: G, GB, T, TB (case-insensitive), or digits + %
_STORAGE_LIMIT_PATTERN = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*%\s*$|^\s*(\d+(?:\.\d+)?)\s*(Gi?B?|Ti?B?)\s*$",
    re.IGNORECASE,
)


def _parse_storage_limit_string(value: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Parse storage_limit config. Returns (number, unit) where unit is '%' or 'bytes'.
    For percentage, number is 0–100. For bytes, we return (None, None) and size in bytes
    is computed in get_server_storage_limit_bytes.
    """
    if not value or not value.strip():
        return (70.0, "%")
    m = _STORAGE_LIMIT_PATTERN.match(value.strip())
    if not m:
        return (None, None)
    if m.group(1) is not None:
        pct = float(m.group(1))
        if 0 < pct <= 100:
            return (pct, "%")
        return (None, None)
    # Size: group(2) = number, group(3) = unit (G, GB, GiB, T, TB, TiB)
    num = float(m.group(2))
    unit = (m.group(3) or "").upper()
    if num <= 0:
        return (None, None)
    # GiB, GB, G -> 1024**3 or 1000**3; TiB, TB, T -> 1024**4 or 1000**4. Use binary (GiB/TiB).
    if "T" in unit:
        return (num * (1024**4), "bytes")
    if "G" in unit:
        return (num * (1024**3), "bytes")
    return (None, None)


def get_disk_usage_bytes(path: Path) -> int:
    """Return total size in bytes of all files under path (recursive)."""
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def get_drive_stats(path: Path) -> Tuple[int, int]:
    """
    Return (total_bytes, free_bytes) for the filesystem containing path.
    Uses os.statvfs (Linux/Unix).
    """
    import os
    try:
        st = os.statvfs(str(path.resolve()))
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        return (total, free)
    except OSError as e:
        log.warning("get_drive_stats failed for %s: %s", path, e)
        return (0, 0)


def get_server_storage_limit_bytes() -> Optional[int]:
    """
    Return the maximum storage (bytes) allowed for all users from config.
    If config is percentage, use that percentage of the total space of the drive
    containing storage_base_path. Returns None if config is invalid (no limit enforced).
    """
    settings = get_settings()
    value = (settings.storage_limit or "").strip() or "70%"
    parsed = _parse_storage_limit_string(value)
    if parsed == (None, None):
        log.warning("Invalid storage_limit config: %r; defaulting to 70%%", value)
        parsed = (70.0, "%")
    num, unit = parsed
    if unit == "%":
        base = settings.storage_base_path
        base.mkdir(parents=True, exist_ok=True)
        total_drive, _ = get_drive_stats(base)
        if total_drive <= 0:
            return None
        return int(total_drive * (num / 100.0))
    if unit == "bytes":
        return int(num)
    return None


def get_user_used_bytes(email: str) -> int:
    """Return bytes used by the given user's storage directory."""
    try:
        base = user_base_path(email)
    except ValueError:
        return 0
    if not base.exists():
        return 0
    return get_disk_usage_bytes(base)


def get_total_used_bytes() -> int:
    """Return total bytes used by all user directories under storage_base_path."""
    settings = get_settings()
    base = settings.storage_base_path
    if not base.exists():
        return 0
    total = 0
    try:
        for entry in base.iterdir():
            if entry.is_dir():
                total += get_disk_usage_bytes(entry)
    except OSError:
        pass
    return total


def get_user_storage_limit_bytes(
    server_limit: Optional[int],
    user_limit_bytes: Optional[int],
) -> Optional[int]:
    """
    Effective storage limit for a user: min(server_limit, user_limit) if both set,
    or the one that is set. Returns None if neither is set (no quota enforced).
    """
    if server_limit is None and user_limit_bytes is None:
        return None
    if server_limit is None:
        return user_limit_bytes
    if user_limit_bytes is None:
        return server_limit
    return min(server_limit, user_limit_bytes)
