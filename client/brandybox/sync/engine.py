"""Sync logic: list local and remote, diff, upload/download, bidirectional deletes."""

import hashlib
import json
import logging
import os
import stat
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# Concurrent transfer tuning (best practices: 8–16 workers for small/mixed files on LAN)
# Backend limit 600/min => max 10 requests/sec; we cap start rate to stay under.
SYNC_MAX_WORKERS = 8
SYNC_RATE_LIMIT_PER_SEC = 10.0  # max transfer starts per second (backend 600/minute)


class _RateLimiter:
    """Limits how often a new transfer may start so we stay under backend rate limit."""

    def __init__(self, per_second: float = SYNC_RATE_LIMIT_PER_SEC) -> None:
        self._interval = 1.0 / per_second if per_second > 0 else 0.0
        self._next_ok = 0.0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        if self._interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            if now < self._next_ok:
                time.sleep(self._next_ok - now)
                now = self._next_ok
            self._next_ok = now + self._interval


def _is_ignored(path_str: str) -> bool:
    """True if the path should be excluded from sync (ignore list or .git)."""
    normalized = path_str.replace("\\", "/")
    # Skip Git metadata: avoids permission issues and keeps sync content-only
    if "/.git/" in normalized or normalized.startswith(".git/"):
        return True
    parts = normalized.split("/")
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


def _load_sync_state() -> dict:
    """Load full sync state (paths, downloaded_paths, file_hashes). Backward compatible."""
    path = get_sync_state_path()
    if not path.exists():
        return {"paths": [], "downloaded_paths": [], "file_hashes": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "paths": data.get("paths") if isinstance(data.get("paths"), list) else [],
            "downloaded_paths": data.get("downloaded_paths") if isinstance(data.get("downloaded_paths"), list) else [],
            "file_hashes": data.get("file_hashes") if isinstance(data.get("file_hashes"), dict) else {},
        }
    except (json.JSONDecodeError, OSError):
        return {"paths": [], "downloaded_paths": [], "file_hashes": {}}


def _save_sync_state(paths: Optional[Set[str]] = None, downloaded_paths: Optional[List[str]] = None, file_hashes: Optional[dict] = None, clear_downloaded_paths: bool = False) -> None:
    """Persist sync state. Pass only keys to update; others are preserved. Set clear_downloaded_paths=True to clear downloaded_paths."""
    state = _load_sync_state()
    if paths is not None:
        state["paths"] = sorted(paths)
    if clear_downloaded_paths:
        state["downloaded_paths"] = []
    elif downloaded_paths is not None:
        state["downloaded_paths"] = downloaded_paths
    if file_hashes is not None:
        state["file_hashes"] = file_hashes
    get_sync_state_path().write_text(
        json.dumps(state, indent=2),
        encoding="utf-8",
    )


def _load_last_synced_paths() -> Set[str]:
    """Load set of paths that were in sync at end of last successful run."""
    return set(_load_sync_state()["paths"])


def _save_last_synced_paths(paths: Set[str], clear_downloaded_paths: bool = False) -> None:
    """Persist set of paths that are now in sync. On full success set clear_downloaded_paths=True."""
    _save_sync_state(paths=paths, clear_downloaded_paths=clear_downloaded_paths)


def _add_downloaded_path(path: str, lock: Optional[threading.Lock] = None) -> None:
    """Append path to downloaded_paths in sync state so next run can skip re-downloading. Thread-safe if lock given."""
    def _do() -> None:
        state = _load_sync_state()
        existing = set(state["downloaded_paths"])
        if path not in existing:
            state["downloaded_paths"] = list(existing | {path})
            _save_sync_state(downloaded_paths=state["downloaded_paths"])
    if lock:
        with lock:
            _do()
    else:
        _do()


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

    Sync state is saved after the delete phase and after each successful upload so that
    closing the app mid-sync does not lose progress. Downloaded paths and content hashes
    are persisted so the next run skips re-downloading files that are already present
    or unchanged (server sends content hash when available).
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

    to_del_list = sorted(to_delete_remote, key=lambda p: -p.count("/"))
    to_del_local_list = sorted(to_delete_local, key=lambda p: -p.count("/"))

    # Build to_download: skip if already downloaded and present, or if content hash matches (server sends hash when available)
    state = _load_sync_state()
    prev_downloaded = set(state["downloaded_paths"])
    file_hashes = state.get("file_hashes") or {}
    to_download = []
    for item in remote_list:
        path = item["path"]
        if _is_ignored(path):
            continue
        remote_mtime = item["mtime"]
        server_hash = item.get("hash")
        parts = path.replace("\\", "/").split("/")
        local_path = local_root.joinpath(*parts)
        if path in prev_downloaded and local_path.exists() and local_path.is_file():
            continue
        if local_path.exists() and local_path.is_file() and server_hash and file_hashes.get(path) == server_hash:
            continue  # content unchanged; skip download
        if not local_path.exists():
            to_download.append(path)
        else:
            try:
                local_mtime = local_path.stat().st_mtime
                if remote_mtime > local_mtime:
                    to_download.append(path)
            except OSError:
                to_download.append(path)

    to_upload = []
    for path, local_mtime in local_list:
        if _is_ignored(path):
            continue
        if path not in remote_by_path:
            to_upload.append(path)
        elif local_mtime > remote_by_path[path]:
            to_upload.append(path)

    total_work = len(to_del_list) + len(to_del_local_list) + len(to_download) + len(to_upload)
    done = 0

    # Delete on server deepest paths first so backend can remove empty parent dirs
    for path in to_del_list:
        try:
            done += 1
            progress("delete_server", done, total_work)
            status(f"Deleting on server {path}…")
            api.delete_file(path)
        except Exception as e:
            log.error("Delete on server %s: %s", path, e)
            return f"Delete on server {path}: {e}"

    # Delete locally deepest first, then remove empty parent dirs
    for path in to_del_local_list:
        try:
            done += 1
            progress("delete_local", done, total_work)
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

    # Persist state after deletes so a mid-sync close doesn't lose progress; next run will only do remaining work.
    base_synced = (current_remote_paths - to_delete_remote)
    base_synced = {p for p in base_synced if not _is_ignored(p)}
    _save_last_synced_paths(base_synced)
    log.debug("Saved sync state after deletes (%d paths)", len(base_synced))

    # 2) Download from server to local (concurrent, rate-limited to stay under backend 600/min)
    log.info("Downloading %d files from server (%d workers)", len(to_download), SYNC_MAX_WORKERS)
    rate_limiter = _RateLimiter(SYNC_RATE_LIMIT_PER_SEC)
    done_lock = threading.Lock()

    def _download_one(path: str) -> Tuple[str, Optional[object], Optional[str]]:
        """Returns (path, None, content_hash) on success, (path, 'skip', None) on skip, (path, exc, None) on error."""
        rate_limiter.acquire()
        try:
            body = api.download_file(path)
            content_hash = hashlib.sha256(body).hexdigest()
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
                                "Download %s: permission denied, skipping: %s",
                                path, write_err,
                            )
                            return (path, "skip", None)
                    else:
                        log.warning("Download %s: permission denied, skipping: %s", path, write_err)
                        return (path, "skip", None)
                return (path, write_err, None)
            return (path, None, content_hash)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                log.debug("Download %s: 404, file no longer on server", path)
                parts = path.replace("\\", "/").split("/")
                local_path = local_root.joinpath(*parts)
                if local_path.exists() and local_path.is_file():
                    local_path.unlink(missing_ok=True)
                return (path, "skip", None)
            return (path, e, None)
        except Exception as e:
            return (path, e, None)

    with ThreadPoolExecutor(max_workers=SYNC_MAX_WORKERS) as executor:
        download_futures = {executor.submit(_download_one, p): p for p in to_download}
        for fut in as_completed(download_futures):
            path, result, content_hash = fut.result()
            with done_lock:
                done += 1
                progress("download", done, total_work)
            status(f"Downloading… ({done - len(to_del_list) - len(to_del_local_list)}/{len(to_download)})")
            if result is not None and result != "skip":
                for f in download_futures:
                    f.cancel()
                err = result if isinstance(result, Exception) else result
                log.error("Download %s: %s", path, err)
                return f"Download {path}: {err}"
            if result is None:
                _add_downloaded_path(path, lock=done_lock)
                if content_hash:
                    with done_lock:
                        state = _load_sync_state()
                        state.setdefault("file_hashes", {})[path] = content_hash
                        _save_sync_state(file_hashes=state["file_hashes"])

    # 3) Upload local additions and newer files to server (concurrent, rate-limited)
    log.info("Uploading %d files to server (%d workers)", len(to_upload), SYNC_MAX_WORKERS)
    done_after_downloads = done
    completed_uploads: Set[str] = set()  # persist after each so mid-sync close can resume
    upload_save_lock = threading.Lock()

    def _upload_one(path: str) -> Tuple[str, Optional[Exception]]:
        """Returns (path, None) on success, (path, exc) on error."""
        rate_limiter.acquire()
        try:
            parts = path.replace("\\", "/").split("/")
            full = local_root.joinpath(*parts)
            body = full.read_bytes()
            api.upload_file(path, body)
            return (path, None)
        except Exception as e:
            return (path, e)

    with ThreadPoolExecutor(max_workers=SYNC_MAX_WORKERS) as executor:
        upload_futures = {executor.submit(_upload_one, p): p for p in to_upload}
        for fut in as_completed(upload_futures):
            path, result = fut.result()
            with done_lock:
                done += 1
                progress("upload", done, total_work)
            status(f"Uploading… ({done - done_after_downloads}/{len(to_upload)})")
            if result is not None:
                for f in upload_futures:
                    f.cancel()
                log.error("Upload %s: %s", path, result)
                return f"Upload {path}: {result}"
            # Persist so closing the app mid-upload lets the next run pick up where we left off
            with upload_save_lock:
                completed_uploads.add(path)
                _save_last_synced_paths(base_synced | completed_uploads)

    # Persist synced paths for next run; clear downloaded_paths so future runs use normal mtime check
    new_synced = (current_remote_paths - to_delete_remote) | set(to_upload)
    new_synced = {p for p in new_synced if not _is_ignored(p)}
    _save_last_synced_paths(new_synced, clear_downloaded_paths=True)
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
