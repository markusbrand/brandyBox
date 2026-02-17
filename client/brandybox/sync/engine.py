"""Sync logic: list local and remote, diff, upload/download."""

from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple

from brandybox.api.client import BrandyBoxAPI


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


def sync_run(
    api: BrandyBoxAPI,
    local_root: Path,
    on_status: Optional[Callable[[str], None]] = None,
) -> Optional[str]:
    """
    Run one sync cycle: list local and remote, then upload new/changed local files,
    download new/changed remote files. Simple strategy: newer mtime wins for conflicts.
    Returns None on success, or an error message string on failure.
    """
    def status(msg: str) -> None:
        if on_status:
            on_status(msg)

    try:
        status("Listing…")
        local_list = _list_local(local_root)
        remote_list = api.list_files()
    except Exception as e:
        return str(e)

    local_set = _local_to_set(local_list)
    remote_set = _remote_to_set(remote_list)
    local_by_path = {p: m for p, m in local_list}
    remote_by_path = {item["path"]: item["mtime"] for item in remote_list}

    # Upload: local file is new or newer than remote
    to_upload: List[str] = []
    for path, local_mtime in local_list:
        if path not in remote_by_path:
            to_upload.append(path)
        elif local_mtime > remote_by_path[path]:
            to_upload.append(path)

    # Download: remote file is new or newer than local
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

    for path in to_upload:
        try:
            status(f"Uploading {path}…")
            parts = path.replace("\\", "/").split("/")
            full = local_root.joinpath(*parts)
            body = full.read_bytes()
            api.upload_file(path, body)
        except Exception as e:
            return f"Upload {path}: {e}"

    for path in to_download:
        try:
            status(f"Downloading {path}…")
            body = api.download_file(path)
            parts = path.replace("\\", "/").split("/")
            target = local_root.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        except Exception as e:
            return f"Download {path}: {e}"

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
