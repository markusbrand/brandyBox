"""Web UI full-page background image stored on disk (not in preferences JSON).

The value ``USER_BACKGROUND_SENTINEL`` is stored in ``UserPreferences.content_background_image``.
The browser fetches the bytes from ``GET /api/users/me/background-image`` with Bearer auth and
uses a blob URL for CSS — plain ``url()`` cannot send the JWT.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

from app.files.storage import resolve_user_path

log = logging.getLogger(__name__)

# Must match web ``USER_BACKGROUND_IMAGE_SENTINEL`` in ``web/src/api/http.ts``.
USER_BACKGROUND_SENTINEL = "bb:server-background"

_REL_FOLDER = ".brandybox"
_NAME_PREFIX = "content-bg"

_MAX_BYTES = 5 * 1024 * 1024


def _user_brandybox_dir(email: str) -> Path:
    return resolve_user_path(email, _REL_FOLDER)


def sniff_image_format(data: bytes) -> Optional[Tuple[str, str]]:
    """Return ``(media_type, file_suffix)`` or ``None`` if not a supported raster image."""
    if len(data) < 12:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return ("image/jpeg", ".jpg")
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return ("image/png", ".png")
    if len(data) >= 6 and data[:6] in (b"GIF87a", b"GIF89a"):
        return ("image/gif", ".gif")
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ("image/webp", ".webp")
    return None


def _suffix_to_media_type(suffix: str) -> str:
    s = suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(s, "application/octet-stream")


def find_stored_background_path(email: str) -> Optional[Tuple[Path, str]]:
    """Return ``(absolute_path, media_type)`` if a stored background file exists."""
    d = _user_brandybox_dir(email)
    if not d.is_dir():
        return None
    for p in sorted(d.glob(f"{_NAME_PREFIX}.*")):
        if p.is_file():
            return (p, _suffix_to_media_type(p.suffix))
    return None


def clear_user_background_image_files(email: str) -> None:
    """Remove stored background image files (best-effort)."""
    d = _user_brandybox_dir(email)
    if not d.is_dir():
        return
    for p in d.glob(f"{_NAME_PREFIX}.*"):
        if p.is_file():
            try:
                p.unlink()
                log.info("Removed user background file email=%s path=%s", email, p.name)
            except OSError as e:
                log.warning("Could not remove background file %s: %s", p, e)


def save_user_background_image_bytes(email: str, data: bytes) -> Tuple[str, str]:
    """
    Validate ``data`` as JPEG/PNG/GIF/WebP, write under ``.brandybox/``, return ``(path_str, media_type)``.

    ``path_str`` is the relative path for logging only.

    Raises:
        ValueError: empty, too large, or not a supported image.
    """
    if not data:
        raise ValueError("Empty body")
    if len(data) > _MAX_BYTES:
        raise ValueError(f"Image too large (max {_MAX_BYTES // (1024 * 1024)} MB)")
    sniffed = sniff_image_format(data)
    if not sniffed:
        raise ValueError("Not a supported image (use JPEG, PNG, GIF, or WebP)")
    media_type, suffix = sniffed

    parent = _user_brandybox_dir(email)
    parent.mkdir(parents=True, exist_ok=True)
    clear_user_background_image_files(email)

    target = parent / f"{_NAME_PREFIX}{suffix}"
    target.write_bytes(data)
    rel = f"{_REL_FOLDER}/{target.name}"
    log.info("Saved user background image email=%s bytes=%d rel=%s", email, len(data), rel)
    return (rel, media_type)
