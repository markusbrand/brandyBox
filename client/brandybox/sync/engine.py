"""Sync logic: list local and remote, diff, upload/download, bidirectional deletes."""

import json
import logging
import os
import stat
import time
from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple

# Progress callback: (phase, current_index, total_count). Phase: "listing"|"delete_server"|"delete_local"|"download"|"upload". total=0 when unknown.
ProgressCallback = Callable[[str, int, int], None]

import httpx

from brandybox.api.client import BrandyBoxAPI
from brandybox.config import get_sync_state_path

log = logging.getLogger(__name__)

# System / file-manager metadata files: not needed for content sync, often read-only or
# cause permission issues on other OS (e.g. .directory on Windows). Never upload or download.
SYNC_IGNORE_BASENAMES: frozenset[str] = frozenset({
    ".directory",   # KDE Dolphin view settings
    "Thumbs.db",    # Windows thumbnail cache
    "Desktop.ini",  # Windows folder customisation
    ".DS_Store",    # macOS Finder metadata
})


def _is_ignored(path_str: str) -> bool:
    """True if the path's basename is in the sync-ignore list."""
    parts = path_str.replace("\\", "/").split("/")
    return parts[-1] in SYNC_IGNORE_BASENAMES if parts else False


def _list_local(root: Path) -> List[Tuple[str, float]]:
    """List files under root with relative path and mtime. Returns [(path, mtime), ...]."""
    out: List[Tuple[str, float]] = []
    try:
        for f in root.rglob("*"):
            if f.is_file():
                try:
                    rel = f.relative_to(root)
                    path_str = str(rel).replace("\\", "/")
                    if _is_ignored(path_str):
                        continue
                    out.append((path_str, f.stat().st_mtime))
                except (OSError, ValueError):
                    continue
    except OSError:
        pass
    return out


def _remote_to_set(remote: List[dict]) -> Set[Tuple[str, float]]:
    """Convert API list response to set of (path, mtime)."""
    return {(item["path"], item["mtime"]) for item in remote}


def _local_to_set(local: List[Tuple[str, float]]) -> Set[Tuple[str, float]]:
    return set(local)


def _load_last_synced_paths() -> Set[str]:
    """Load set of paths that were in sync at end of last successful run."""
    path = get_sync_state_path()
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        paths = data.get("paths")
        return set(paths) if isinstance(paths, list) else set()
    except (json.JSONDecodeError, OSError):
        return set()


def _save_last_synced_paths(paths: Set[str]) -> None:
    """Persist set of paths that are now in sync (after this run)."""
    get_sync_state_path().write_text(
        json.dumps({"paths": sorted(paths)}, indent=2),
        encoding="utf-8",
    )


def sync_run(
    api: BrandyBoxAPI,
    local_root: Path,
    on_status: Optional[Callable[[str], None]] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> Optional[str]:
    """
    Run one sync cycle: (1) list server and local; (2) propagate deletions (local→server,
    server→local); (3) download from server to local (server is source of truth);
    (4) upload local additions and newer files to server. Returns None on success,
    or an error message on failure.
    """
    def status(msg: str) -> None:
        if on_status:
            on_status(msg)

    def progress(phase: str, current: int, total: int) -> None:
        if on_progress:
            on_progress(phase, current, total)

    log.info("Sync cycle started (local_root=%s)", local_root)
    try:
        status("Listing…")
        progress("listing", 0, 0)
        local_list = _list_local(local_root)
        remote_list = api.list_files()
    except Exception as e:
        log.exception("Sync failed at list: %s", e)
        return str(e)

    local_by_path = {p: m for p, m in local_list}
    remote_by_path = {item["path"]: item["mtime"] for item in remote_list}
    current_local_paths = set(local_by_path)
    current_remote_paths = set(remote_by_path)
    last_synced = _load_last_synced_paths()
    log.info("Listed %d local files, %d remote files, %d in last_synced", len(current_local_paths), len(current_remote_paths), len(last_synced))

    # 1) Propagate deletions: local deletes → server, server deletes → local
    to_delete_remote = {p for p in (last_synced - current_local_paths) if not _is_ignored(p)}
    to_delete_local = last_synced - current_remote_paths  # gone from remote (e.g. other client)
    log.debug("Deletions: %d from server, %d from local", len(to_delete_remote), len(to_delete_local))

    # Delete on server deepest paths first so backend can remove empty parent dirs
    to_del_list = sorted(to_delete_remote, key=lambda p: -p.count("/"))
    for i, path in enumerate(to_del_list):
        try:
            progress("delete_server", i + 1, len(to_del_list) if to_del_list else 0)
            status(f"Deleting on server {path}…")
            api.delete_file(path)
        except Exception as e:
            log.error("Delete on server %s: %s", path, e)
            return f"Delete on server {path}: {e}"

    # Delete locally deepest first, then remove empty parent dirs
    to_del_local_list = sorted(to_delete_local, key=lambda p: -p.count("/"))
    for i, path in enumerate(to_del_local_list):
        try:
            progress("delete_local", i + 1, len(to_del_local_list) if to_del_local_list else 0)
            parts = path.replace("\\", "/").split("/")
            local_path = local_root.joinpath(*parts)
            if local_path.exists() and local_path.is_file():
                status(f"Deleting locally {path}…")
                local_path.unlink(missing_ok=True)
                # Remove empty parent directories
                parent = local_path.parent
                while parent != local_root and parent.exists():
                    try:
                        if not any(parent.iterdir()):
                            parent.rmdir()
                            parent = parent.parent
                        else:
                            break
                    except OSError:
                        break
        except Exception as e:
            log.error("Delete locally %s: %s", path, e)
            return f"Delete locally {path}: {e}"

    # 2) Download from server to local (server is source of truth for existing files)
    remote_list_tuples = [(item["path"], item["mtime"]) for item in remote_list]
    to_download: List[str] = []
    for path, remote_mtime in remote_list_tuples:
        if _is_ignored(path):
            continue
        parts = path.replace("\\", "/").split("/")
        local_path = local_root.joinpath(*parts)
        if not local_path.exists():
            to_download.append(path)
        else:
            try:
                local_mtime = local_path.stat().st_mtime
                if remote_mtime > local_mtime:
                    to_download.append(path)
            except OSError:
                to_download.append(path)

    log.info("Downloading %d files from server", len(to_download))
    for i, path in enumerate(to_download):
        try:
            progress("download", i + 1, len(to_download))
            status(f"Downloading {path}…")
            body = api.download_file(path)
            parts = path.replace("\\", "/").split("/")
            target = local_root.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                target.write_bytes(body)
            except (PermissionError, OSError) as write_err:
                if getattr(write_err, "errno", None) == 13 or isinstance(write_err, PermissionError):
                    if target.exists() and target.is_file():
                        try:
                            os.chmod(target, stat.S_IMODE(target.stat().st_mode) | stat.S_IWUSR)
                            target.write_bytes(body)
                        except Exception:
                            log.warning(
                                "Download %s: permission denied (e.g. read-only or policy), skipping: %s",
                                path, write_err,
                            )
                            continue
                    else:
                        log.warning(
                            "Download %s: permission denied, skipping: %s",
                            path, write_err,
                        )
                        continue
                raise
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # File was removed on server (e.g. by us in this cycle or another client); skip and remove locally if present
                log.debug("Download %s: 404, file no longer on server", path)
                parts = path.replace("\\", "/").split("/")
                local_path = local_root.joinpath(*parts)
                if local_path.exists() and local_path.is_file():
                    local_path.unlink(missing_ok=True)
                continue
            log.error("Download %s: %s", path, e)
            return f"Download {path}: {e}"
        except Exception as e:
            log.error("Download %s: %s", path, e)
            return f"Download {path}: {e}"

    # 3) Upload local additions and newer files to server
    to_upload: List[str] = []
    for path, local_mtime in local_list:
        if path not in remote_by_path:
            to_upload.append(path)
        elif local_mtime > remote_by_path[path]:
            to_upload.append(path)

    log.info("Uploading %d files to server", len(to_upload))
    # Throttle uploads to stay under backend rate limit (600/min = 10/sec)
    UPLOAD_DELAY = 0.12  # ~8 uploads/sec
    for i, path in enumerate(to_upload):
        try:
            if i > 0:
                time.sleep(UPLOAD_DELAY)
            progress("upload", i + 1, len(to_upload))
            status(f"Uploading {path}…")
            parts = path.replace("\\", "/").split("/")
            full = local_root.joinpath(*parts)
            body = full.read_bytes()
            api.upload_file(path, body)
        except Exception as e:
            log.error("Upload %s: %s", path, e)
            return f"Upload {path}: {e}"

    # Persist synced paths for next run (remote state after our deletes and uploads)
    new_synced = (current_remote_paths - to_delete_remote) | set(to_upload)
    new_synced = {p for p in new_synced if not _is_ignored(p)}
    _save_last_synced_paths(new_synced)
    log.info("Sync cycle completed (synced paths: %d)", len(new_synced))

    return None


class SyncEngine:
    """
    Wraps sync_run and can be used from a timer/thread to run periodic sync.
    """

    def __init__(
        self,
        api: BrandyBoxAPI,
        local_root: Path,
        on_status: Optional[Callable[[str], None]] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> None:
        self._api = api
        self._local_root = local_root
        self._on_status = on_status
        self._on_progress = on_progress

    def run(self) -> Optional[str]:
        """Run one sync cycle. Returns None on success, error message on failure."""
        return sync_run(
            self._api,
            self._local_root,
            on_status=self._on_status,
            on_progress=self._on_progress,
        )
