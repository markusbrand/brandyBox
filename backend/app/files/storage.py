"""Safe path resolution under base dir (no directory traversal)."""

import re
from pathlib import Path
from typing import List, Optional

from app.config import get_settings

# Safe path segment for file/dir names (no @ to avoid ambiguity)
_SAFE_SEGMENT = re.compile(r"^[a-zA-Z0-9_.-]+$")
# Email used as folder name: allow @ and dots
_SAFE_EMAIL = re.compile(r"^[a-zA-Z0-9_.@-]+$")


def _sanitize_segment(segment: str) -> Optional[str]:
    """Return segment if safe, else None. Rejects empty, '..', '.', and invalid chars."""
    segment = segment.strip()
    if not segment or segment in (".", ".."):
        return None
    if not _SAFE_SEGMENT.match(segment):
        return None
    return segment


def _sanitize_email_for_path(email: str) -> Optional[str]:
    """Return email if safe for use as a single path segment (no traversal)."""
    email = email.strip()
    if not email or ".." in email or "/" in email or "\\" in email:
        return None
    if not _SAFE_EMAIL.match(email):
        return None
    return email


def user_base_path(email: str) -> Path:
    """Return the filesystem path for a user's root (base / email)."""
    settings = get_settings()
    safe_email = _sanitize_email_for_path(email)
    if not safe_email:
        raise ValueError("Invalid email for path")
    return settings.storage_base_path / safe_email


def resolve_user_path(email: str, relative_path: str) -> Path:
    """
    Resolve a relative path under the user's folder. Rejects traversal and unsafe names.
    relative_path uses forward slashes; segments are sanitized.
    """
    base = user_base_path(email)
    parts = relative_path.replace("\\", "/").strip("/").split("/")
    resolved = base
    for part in parts:
        if not part:
            continue
        safe = _sanitize_segment(part)
        if not safe:
            raise ValueError(f"Unsafe path segment: {part!r}")
        resolved = resolved / safe
    return resolved


def list_files_recursive(root: Path) -> List[dict]:
    """
    List all files under root with relative path and mtime.
    Returns list of {"path": str, "mtime": float} for files only.
    """
    result: List[dict] = []
    try:
        for f in root.rglob("*"):
            if f.is_file():
                try:
                    rel = f.relative_to(root)
                    result.append({
                        "path": str(rel).replace("\\", "/"),
                        "mtime": f.stat().st_mtime,
                    })
                except (OSError, ValueError):
                    continue
    except OSError:
        pass
    return result
