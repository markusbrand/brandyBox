"""Sync logic: list local and remote, diff, upload/download, bidirectional deletes.

Multi-client design: any number of clients (Windows, Linux, macOS) can use the same
account and sync folder; each has its own per-machine sync state (config dir).
Last change wins: deletions propagate (delete on one client → server → other clients
delete locally); file content uses content hash when available, else mtime (newer
overwrites older). No conflict merge — concurrent edits resolve by hash match or
timestamp.

Robustness principles:
- Only mark a path as "in sync" when we have verified it exists on both sides with
  matching content. Never add paths we failed to download/upload.
- Track skipped operations separately; do not pollute sync state.
- Operations are idempotent where possible (e.g. delete 404 = success).
"""

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
# Warnings callback: called when sync completes with non-fatal issues (e.g. skipped uploads due to file removed during sync)
WarningsCallback = Callable[[int, List[str]], None]

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
    on_complete: Optional[Callable[[int, int], None]] = None,
    on_warnings: Optional[WarningsCallback] = None,
) -> Optional[str]:
    """
    Run one sync cycle: (1) list server and local; (2) propagate deletions (local→server,
    server→local); (3) download from server to local (server is source of truth);
    (4) upload local additions and newer files to server. Returns None on success,
    or an error message on failure. On success, calls on_complete(downloaded, uploaded)
    with the number of files actually downloaded and uploaded.

    Safe for multiple clients on different machines/OS: each client has its own
    sync state; deletions and updates propagate so last change wins (by mtime for
    content, and delete-on-one-client becomes delete-on-server then delete-on-others).

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

    # --- Phase 1: List both sides (authoritative snapshot) ---
    try:
        status("Listing…")
        progress("listing", 0, 0)
        local_list = _list_local(local_root)
        remote_list = api.list_files()
    except Exception as e:
        # Connection refused / unreachable is expected when local backend is down; we retry with remote.
        if isinstance(e, httpx.ConnectError) or "connection refused" in str(e).lower():
            log.warning("Backend unreachable at list: %s (will retry with other URL or later)", e)
        else:
            log.exception("Sync failed at list: %s", e)
        return str(e)

    local_by_path = {p: m for p, m in local_list}
    remote_by_path = {item["path"]: item["mtime"] for item in remote_list}
    current_local_paths = set(local_by_path)
    current_remote_paths = set(remote_by_path)
    last_synced = _load_last_synced_paths()
    log.info("Listed %d local files, %d remote files, %d in last_synced", len(current_local_paths), len(current_remote_paths), len(last_synced))
    only_remote = current_remote_paths - current_local_paths
    only_local = current_local_paths - current_remote_paths
    if only_remote:
        ignored_remote = sum(1 for p in only_remote if _is_ignored(p))
        if ignored_remote == len(only_remote):
            log.debug("All %d paths only on server are ignored (.git, .directory, etc.); no download needed", len(only_remote))
        else:
            log.debug("%d paths only on server (%d ignored); %d paths only local", len(only_remote), ignored_remote, len(only_local))

    # --- Phase 2: Compute deletions from last_synced vs current state ---
    # Only treat "missing locally" as "delete on server" for paths we actually had locally (last_synced
    # should mean "in sync on both sides"). Otherwise a new/empty client would mark all remote paths
    # as in-sync before downloading and then delete them on the next run.
    to_delete_remote = {p for p in (last_synced - current_local_paths) if not _is_ignored(p)}
    to_delete_local = last_synced - current_remote_paths  # gone from remote → delete locally (other client deleted it)
    log.debug("Deletions: %d from server, %d from local", len(to_delete_remote), len(to_delete_local))

    # Safety: never delete more files on server than we have locally when the number is large.
    # Prevents wiping server when sync state is wrong (new device, wrong folder, or corrupted state).
    if len(to_delete_remote) > 50 and len(to_delete_remote) > len(current_local_paths):
        log.warning(
            "Skipping server deletes: would delete %d on server but only %d files locally; "
            "likely new device or wrong sync folder. Downloading from server instead.",
            len(to_delete_remote), len(current_local_paths),
        )
        to_delete_remote = set()
        to_del_list = []
    else:
        to_del_list = sorted(to_delete_remote, key=lambda p: -p.count("/"))
    to_del_local_list = sorted(to_delete_local, key=lambda p: -p.count("/"))

    # Build to_download: skip if already downloaded and present, or if content hash matches (server sends hash when available).
    # When state has no hash for a path but local file exists and server sends hash, compute local hash and skip if equal
    # so we don't re-download after a folder change or state clear.
    state = _load_sync_state()
    prev_downloaded = set(state["downloaded_paths"])
    file_hashes = dict(state.get("file_hashes") or {})
    verified_hashes: dict = {}  # path -> hash for files we verified locally this run (to persist)
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
            continue  # content unchanged (from state); skip download
        if not local_path.exists():
            to_download.append(path)
        else:
            try:
                local_mtime = local_path.stat().st_mtime
                if remote_mtime > local_mtime:
                    # Before re-downloading, check if local content already matches server (e.g. after folder change or state clear)
                    if server_hash:
                        try:
                            local_hash = hashlib.sha256(local_path.read_bytes()).hexdigest()
                            if local_hash == server_hash:
                                verified_hashes[path] = server_hash
                                continue
                        except OSError:
                            pass
                    to_download.append(path)
            except OSError:
                to_download.append(path)
    if verified_hashes:
        file_hashes.update(verified_hashes)
        _save_sync_state(file_hashes=file_hashes)
        log.info("Skipped %d downloads (local content matches server hash); updated file_hashes", len(verified_hashes))

    # Build to_upload: new files, or local newer than remote. Use content hash when
    # available to avoid spurious uploads from clock skew.
    remote_by_item = {item["path"]: item for item in remote_list}
    to_upload = []
    for path, local_mtime in local_list:
        if _is_ignored(path):
            continue
        remote = remote_by_item.get(path)
        if remote is None:
            to_upload.append(path)
            continue
        remote_mtime = remote["mtime"]
        server_hash = remote.get("hash")
        if server_hash:
            # Hash available: skip upload if local content matches (avoids clock skew)
            try:
                parts = path.replace("\\", "/").split("/")
                local_path = local_root.joinpath(*parts)
                if local_path.exists() and local_path.is_file():
                    local_hash = hashlib.sha256(local_path.read_bytes()).hexdigest()
                    if local_hash == server_hash:
                        continue  # Already in sync
            except (OSError, MemoryError):
                pass
        if local_mtime > remote_mtime:
            to_upload.append(path)

    # Warn if we're about to download a huge number of files (possible sync-folder mismatch, e.g. brandyBox vs brandybox on Linux)
    if len(to_download) > 1000 and len(to_download) > 10 * max(len(to_upload), 1) and len(last_synced) > 0:
        log.warning(
            "Sync would download %d files but only upload %d; sync folder may be wrong (e.g. check case: brandyBox vs brandybox). Current folder: %s",
            len(to_download), len(to_upload), local_root,
        )

    total_work = len(to_del_list) + len(to_del_local_list) + len(to_download) + len(to_upload)
    done = 0

    # --- Phase 3: Execute deletions (server first, then local) ---
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

    # Persist state after deletes so a mid-sync close doesn't lose progress. Only mark paths as "in sync"
    # when they exist on both sides (we have them locally). Otherwise a new/empty client would record all
    # remote paths here, then on the next run treat "missing locally" as delete-on-server and wipe the server.
    remaining_local = current_local_paths - to_delete_local
    remaining_remote = current_remote_paths - to_delete_remote
    base_synced = {p for p in (remaining_remote & remaining_local) if not _is_ignored(p)}
    _save_last_synced_paths(base_synced)
    log.debug("Saved sync state after deletes (%d paths, only those present locally)", len(base_synced))

    # --- Phase 4: Download from server (concurrent, rate-limited) ---
    log.info("Downloading %d files from server (%d workers)", len(to_download), SYNC_MAX_WORKERS)
    rate_limiter = _RateLimiter(SYNC_RATE_LIMIT_PER_SEC)
    done_lock = threading.Lock()
    n_downloaded = 0
    n_uploaded = 0  # set in upload phase
    completed_downloads: Set[str] = set()  # paths we successfully downloaded (for new_synced)
    skipped_downloads: Set[str] = set()  # paths we skipped (permission, 404) - exclude from new_synced

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
            if result == "skip":
                skipped_downloads.add(path)
            if result is None:
                n_downloaded += 1
                completed_downloads.add(path)
                _add_downloaded_path(path, lock=done_lock)
                if content_hash:
                    with done_lock:
                        state = _load_sync_state()
                        state.setdefault("file_hashes", {})[path] = content_hash
                        _save_sync_state(file_hashes=state["file_hashes"])

    # --- Phase 5: Upload to server (concurrent, rate-limited) ---
    log.info("Uploading %d files to server (%d workers)", len(to_upload), SYNC_MAX_WORKERS)
    done_after_downloads = done
    completed_uploads: Set[str] = set()  # persist after each so mid-sync close can resume
    skipped_uploads: Set[str] = set()  # file no longer present (removed during sync) - don't add to new_synced
    upload_save_lock = threading.Lock()

    def _upload_one(path: str) -> Tuple[str, Optional[object]]:
        """Returns (path, None) on success, (path, 'skip') if file missing, (path, exc) on error."""
        rate_limiter.acquire()
        try:
            parts = path.replace("\\", "/").split("/")
            full = local_root.joinpath(*parts)
            body = full.read_bytes()
            api.upload_file(path, body)
            return (path, None)
        except MemoryError as e:
            log.error("Upload %s: out of memory (file too large to load), consider excluding large files: %s", path, e)
            return (path, e)
        except (FileNotFoundError, OSError) as e:
            if getattr(e, "errno", None) == 2 or isinstance(e, FileNotFoundError):
                log.debug("Upload %s: file no longer present, skipping", path)
                return (path, "skip")
            return (path, e)
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
            if result is not None and result != "skip":
                for f in upload_futures:
                    f.cancel()
                log.error("Upload %s: %s", path, result)
                return f"Upload {path}: {result}"
            if result == "skip":
                skipped_uploads.add(path)
            if result is None:
                n_uploaded += 1
                # Persist so closing the app mid-upload lets the next run pick up where we left off
                with upload_save_lock:
                    completed_uploads.add(path)
                    _save_last_synced_paths(base_synced | completed_uploads)

    # Log skipped uploads once (avoid log spam when many files removed during sync)
    if skipped_uploads:
        sample = sorted(skipped_uploads)[:5]
        log.warning(
            "Skipped %d uploads (file no longer present during sync, e.g. removed by another process): sample=%s",
            len(skipped_uploads), sample,
        )
        if on_warnings:
            on_warnings(len(skipped_uploads), list(sample))

    if skipped_downloads:
        sample = sorted(skipped_downloads)[:5]
        log.warning(
            "Skipped %d downloads (permission denied or file gone): sample=%s",
            len(skipped_downloads), sample,
        )

    # --- Phase 6: Persist verified sync state ---
    # Only paths we verified exist on both sides with correct content.
    # Never add paths we failed/skipped to download or upload (prevents discrepancy and wrong deletes).
    new_synced = (base_synced | completed_downloads | completed_uploads) - skipped_uploads
    new_synced = {p for p in new_synced if not _is_ignored(p)}
    _save_last_synced_paths(new_synced, clear_downloaded_paths=True)
    log.info("Sync cycle completed (synced paths: %d)", len(new_synced))

    if on_complete and (n_downloaded > 0 or n_uploaded > 0):
        on_complete(n_downloaded, n_uploaded)
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
        on_complete: Optional[Callable[[int, int], None]] = None,
        on_warnings: Optional[WarningsCallback] = None,
    ) -> None:
        self._api = api
        self._local_root = local_root
        self._on_status = on_status
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_warnings = on_warnings

    def run(self) -> Optional[str]:
        """Run one sync cycle. Returns None on success, error message on failure."""
        return sync_run(
            self._api,
            self._local_root,
            on_status=self._on_status,
            on_progress=self._on_progress,
            on_complete=self._on_complete,
            on_warnings=self._on_warnings,
        )
