"""File API routes: list, upload, download, delete."""

import hashlib
import logging
import os
import shutil
import tempfile
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.files.hash_store import (
    get_hashes_for_paths,
    set_hash,
    delete_hash,
    get_hasher,
)
from app.files.quota import (
    get_server_storage_limit_bytes,
    get_user_storage_limit_bytes,
    get_user_used_bytes,
    get_total_used_bytes,
    get_drive_stats,
)
from app.config import get_settings
from app.files.storage import delete_file as storage_delete_file
from app.files.storage import (
    list_directories_recursive,
    list_files_recursive,
    make_directory,
    resolve_user_path,
    user_base_path,
)
from app.limiter import limiter
from app.users.models import User

router = APIRouter(prefix="/api/files", tags=["files"])
log = logging.getLogger(__name__)


def _normalize_path_param(path: Optional[str]) -> str:
    """Return path from query string. Do not replace + with space: filenames may contain +."""
    return path or ""


@router.get("/storage")
@limiter.limit("60/minute")
async def get_storage(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Return current user's storage used/limit and server (Pi) disk usage in bytes (for settings UI)."""
    used = get_user_used_bytes(current_user.email)
    server_limit = get_server_storage_limit_bytes()
    effective_limit = get_user_storage_limit_bytes(server_limit, current_user.storage_limit_bytes)
    result = {"used_bytes": used, "limit_bytes": effective_limit}
    # Add server (Raspberry Pi) overall disk usage. Use server_disk_path if set (e.g. /mnt/shared_storage
    # for full HDD), else the filesystem containing storage_base_path.
    try:
        settings = get_settings()
        use_server_disk_path = (
            settings.server_disk_path is not None and str(settings.server_disk_path).strip()
        )
        disk_path = settings.server_disk_path.resolve() if use_server_disk_path else settings.storage_base_path
        if not use_server_disk_path:
            settings.storage_base_path.mkdir(parents=True, exist_ok=True)
        total_disk, free_disk = get_drive_stats(disk_path)
        if total_disk > 0:
            result["server_disk_total_bytes"] = total_disk
            result["server_disk_used_bytes"] = total_disk - free_disk
            result["server_disk_path"] = str(disk_path)  # so client/debug can show which path was used
            log.info(
                "Server disk stats: path=%s total=%s used=%s",
                disk_path,
                total_disk,
                total_disk - free_disk,
            )
    except Exception as e:
        try:
            s = get_settings()
            path = getattr(s, "server_disk_path", None) or s.storage_base_path
        except Exception:
            path = "?"
        log.warning("Server disk stats unavailable (path=%s): %s", path, e)
    return result


@router.get("/list", response_model=List[dict])
@limiter.limit("60/minute")
async def list_files(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> List[dict]:
    """List all files for the current user (recursive, ``path`` + ``mtime`` + ``size`` + optional ``hash``).

    The ``size`` field was added in API 0.3.0 and is sent as bytes (int).
    Older clients ignore unknown fields, so the response stays backward
    compatible.
    """
    base = user_base_path(current_user.email)
    base.mkdir(parents=True, exist_ok=True)
    result = list_files_recursive(base)
    paths = [r["path"] for r in result]
    hashes = await get_hashes_for_paths(session, current_user.email, paths)
    for r in result:
        if r["path"] in hashes:
            r["hash"] = hashes[r["path"]]
    log.info("list_files user=%s count=%d", current_user.email, len(result))
    return result


@router.get("/folders", response_model=List[dict])
@limiter.limit("60/minute")
async def list_folders(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[dict]:
    """List all directories for the current user (recursive, ``path`` + ``mtime``).

    Added in API 0.3.0 to let the web file browser render *empty* folders
    that the user created via ``POST /api/files/mkdir`` (folders that hold
    no files cannot be inferred from the file list). The user's root itself
    is not included. Sync clients do not need to call this endpoint —
    creating empty folders is purely a web UI feature.
    """
    base = user_base_path(current_user.email)
    base.mkdir(parents=True, exist_ok=True)
    result = list_directories_recursive(base)
    log.info("list_folders user=%s count=%d", current_user.email, len(result))
    return result


@router.post("/mkdir")
@limiter.limit("60/minute")
async def make_folder(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Create an empty folder under the user's root.

    Idempotent: returns ``{"path": ..., "created": false}`` if the folder
    already exists. Returns 409 if a file with that name already exists.
    Path segments are sanitized (no traversal, no unsafe characters).

    Added in API 0.3.0; primarily used by the web file browser so users can
    create folders before uploading anything into them.
    """
    path_param = _normalize_path_param(request.query_params.get("path"))
    if not path_param or not path_param.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'path' is required",
        )
    try:
        result = make_directory(current_user.email, path_param)
    except ValueError as e:
        log.warning("make_folder rejected path=%r: %s", path_param, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FileExistsError as e:
        log.warning("make_folder conflict path=%r: %s", path_param, e)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except OSError as e:
        log.exception("make_folder failed path=%r: %s", path_param, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create folder",
        )
    log.info(
        "make_folder user=%s path=%s created=%s",
        current_user.email, path_param, result["created"],
    )
    return result


@router.post("/upload")
@limiter.limit("600/minute")  # Bulk sync
async def upload_file(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Upload a file by streaming the request body directly to a temporary file.
    Enforces quota during streaming to fail fast.
    """
    path_param = _normalize_path_param(request.query_params.get("path"))
    if not path_param or not path_param.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'path' is required",
        )
    try:
        target = resolve_user_path(current_user.email, path_param)
    except ValueError as e:
        log.warning("upload_file rejected path=%r: %s", path_param, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Determine quotas before starting
    old_size = 0
    if target.exists() and target.is_file():
        try:
            old_size = target.stat().st_size
        except OSError:
            pass

    server_limit = get_server_storage_limit_bytes()
    user_limit = get_user_storage_limit_bytes(server_limit, current_user.storage_limit_bytes)
    total_used_before = get_total_used_bytes()
    user_used_before = get_user_used_bytes(current_user.email)

    settings = get_settings()
    max_body = settings.max_single_upload_bytes

    hasher = get_hasher()
    bytes_written = 0

    # Stream to a temporary file
    temp_dir = target.parent
    temp_dir.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(dir=temp_dir, prefix=".bb_upload_")
    try:
        with os.fdopen(fd, "wb") as f:
            async for chunk in request.stream():
                if not chunk:
                    continue

                current_size = bytes_written + len(chunk)
                if max_body is not None and current_size > max_body:
                    log.warning(
                        "upload_file rejected path=%r: body exceeds max_single_upload_bytes (%s)",
                        path_param,
                        max_body,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Upload exceeds configured maximum size",
                    )

                # Quota check during streaming
                if server_limit is not None:
                    if total_used_before - old_size + current_size > server_limit:
                        raise HTTPException(status_code=507, detail="Server storage limit reached")
                if user_limit is not None:
                    if user_used_before - old_size + current_size > user_limit:
                        raise HTTPException(status_code=507, detail="Your storage limit has been reached")

                f.write(chunk)
                hasher.update(chunk)
                bytes_written += len(chunk)

        # Atomic move to final destination
        shutil.move(temp_path, target)
        content_hash = hasher.hexdigest()
        await set_hash(session, current_user.email, path_param, content_hash)

        log.info(
            "upload_file user=%s path=%s size=%d resolved=%s",
            current_user.email, path_param, bytes_written, target
        )
        return {"path": path_param, "size": bytes_written, "hash": content_hash}

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if isinstance(e, HTTPException):
            raise e
        log.exception("Upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error during upload")


@router.get("/download")
@limiter.limit("600/minute")  # Bulk sync: same as upload
async def download_file(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """
    Download a file. Query param: path (relative path).
    """
    path_param = _normalize_path_param(request.query_params.get("path"))
    if not path_param or not path_param.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'path' is required",
        )
    try:
        target = resolve_user_path(current_user.email, path_param)
    except ValueError as e:
        log.warning("download_file rejected path=%r: %s", path_param, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    if not target.exists() or not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    log.info("download_file user=%s path=%s", current_user.email, path_param)
    return FileResponse(
        path=target,
        filename=target.name,
        media_type="application/octet-stream",
    )


@router.delete("/delete")
@limiter.limit("600/minute")  # Bulk sync
async def delete_file(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Delete a file. Query param: path (relative path).
    Propagates deletion so other clients will remove the file on next sync.
    """
    path_param = _normalize_path_param(request.query_params.get("path"))
    if not path_param or not path_param.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'path' is required",
        )
    try:
        storage_delete_file(current_user.email, path_param)
    except ValueError as e:
        log.warning("delete_file rejected path=%r: %s", path_param, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    await delete_hash(session, current_user.email, path_param)
    log.info("delete_file user=%s path=%s", current_user.email, path_param)
    return {"path": path_param, "deleted": True}
