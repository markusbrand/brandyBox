"""Sync logic: list local and remote, diff, upload/download, bidirectional deletes."""

import json
import logging
from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple

from brandybox.api.client import BrandyBoxAPI
from brandybox.config import get_sync_state_path

log = logging.getLogger(__name__)


def _list_local(root: Path) -> List[Tuple[str, float]]:
    """List files under root with relative path and mtime. Returns [(path, mtime), ...]."""
    out: List[Tuple[str, float]] = []
    try:
        for f in root.rglob("*"):
            if f.is_file():
                try:
                    rel = f.relative_to(root)
                    path_str = str(rel).replace("\\", "/")
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

    log.info("Sync cycle started (local_root=%s)", local_root)
    try:
        status("Listing…")
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
    to_delete_remote = last_synced - current_local_paths  # we removed these locally
    to_delete_local = last_synced - current_remote_paths  # gone from remote (e.g. other client)
    log.debug("Deletions: %d from server, %d from local", len(to_delete_remote), len(to_delete_local))

    for path in to_delete_remote:
        try:
            status(f"Deleting on server {path}…")
            api.delete_file(path)
        except Exception as e:
            log.error("Delete on server %s: %s", path, e)
            return f"Delete on server {path}: {e}"

    for path in to_delete_local:
        try:
            parts = path.replace("\\", "/").split("/")
            local_path = local_root.joinpath(*parts)
            if local_path.exists() and local_path.is_file():
                status(f"Deleting locally {path}…")
                local_path.unlink(missing_ok=True)
        except Exception as e:
            log.error("Delete locally %s: %s", path, e)
            return f"Delete locally {path}: {e}"

    # 2) Download from server to local (server is source of truth for existing files)
    remote_list_tuples = [(item["path"], item["mtime"]) for item in remote_list]
    to_download: List[str] = []
    for path, remote_mtime in remote_list_tuples:
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
    for path in to_download:
        try:
            status(f"Downloading {path}…")
            body = api.download_file(path)
            parts = path.replace("\\", "/").split("/")
            target = local_root.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
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
    for path in to_upload:
        try:
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
    ) -> None:
        self._api = api
        self._local_root = local_root
        self._on_status = on_status

    def run(self) -> Optional[str]:
        """Run one sync cycle. Returns None on success, error message on failure."""
        return sync_run(self._api, self._local_root, self._on_status)
