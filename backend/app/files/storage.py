"""Safe path resolution under base dir (no directory traversal)."""

import re
import unicodedata
from pathlib import Path
from typing import List, Optional

from app.config import get_settings

# Safe path segment: letters, numbers, common punctuation. No / \ (traversal).
# Allow: . _ - space ( ) + ~ # ! & ' , ; = [ ] @ for "File (1).txt", "user@host.txt", etc.
_SAFE_SEGMENT_ASCII = re.compile(r"^[a-zA-Z0-9_. \-()+~#!&',;=\[\]@]+$")
# Email used as folder name: allow @ and dots
_SAFE_EMAIL = re.compile(r"^[a-zA-Z0-9_.@-]+$")


def _is_safe_path_char(c: str) -> bool:
    """True if char is allowed in a path segment (no traversal, no control chars)."""
    if len(c) != 1:
        return False
    if c in "/\\%":
        return False  # % can be used in encoding/URLs; keep path segments safe
    if ord(c) < 32:
        return False
    if ("a" <= c <= "z") or ("A" <= c <= "Z") or ("0" <= c <= "9") or c in "_. -()+~#!&',;=[]@":
        return True
    cat = unicodedata.category(c)
    # Letter, Number, or Punctuation (e.g. fullwidth parentheses （） in "Manual（CN）.pdf")
    return cat.startswith("L") or cat.startswith("N") or cat.startswith("P")


def _sanitize_segment(segment: str) -> Optional[str]:
    """Return segment if safe, else None. Rejects empty, '..', '.', and invalid chars.
    Allows Unicode letters and numbers (e.g. ä, ö, ü, é) for international filenames.
    """
    segment = segment.strip()
    if not segment or segment in (".", ".."):
        return None
    if _SAFE_SEGMENT_ASCII.match(segment):
        return segment
    if not all(_is_safe_path_char(c) for c in segment):
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


def delete_file(email: str, relative_path: str) -> None:
    """
    Delete a file under the user's folder. Rejects traversal and unsafe names.
    After deleting the file, removes any now-empty parent directories up to (but not
    including) the user base path so folder deletions stay in sync.
    Raises ValueError for invalid path; raises FileNotFoundError if file does not exist.
    """
    base = user_base_path(email)
    target = resolve_user_path(email, relative_path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {relative_path}")
    if not target.is_file():
        raise ValueError(f"Not a file: {relative_path}")
    target.unlink()
    # Remove empty parent directories so folder deletions propagate
    parent = target.parent
    while parent != base and parent.exists():
        try:
            if not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
            else:
                break
        except OSError:
            break


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
