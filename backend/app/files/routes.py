"""File API routes: list, upload, download, delete."""

import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.files.hash_store import compute_hash, get_hashes_for_paths, set_hash, delete_hash
from app.files.quota import (
    get_server_storage_limit_bytes,
    get_user_storage_limit_bytes,
    get_user_used_bytes,
    get_total_used_bytes,
)
from app.files.storage import delete_file as storage_delete_file
from app.files.storage import list_files_recursive, resolve_user_path, user_base_path
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
    """Return current user's storage used and limit in bytes (for settings UI)."""
    used = get_user_used_bytes(current_user.email)
    server_limit = get_server_storage_limit_bytes()
    effective_limit = get_user_storage_limit_bytes(server_limit, current_user.storage_limit_bytes)
    return {"used_bytes": used, "limit_bytes": effective_limit}


@router.get("/list", response_model=List[dict])
@limiter.limit("60/minute")
async def list_files(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> List[dict]:
    """List all files for the current user (recursive, path + mtime + optional content_hash)."""
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


@router.post("/upload")
@limiter.limit("600/minute")  # Bulk sync: allow ~10 uploads/sec so 18k files finish in ~30 min
async def upload_file(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Upload a file. Query param: path (relative path). Body: raw file bytes.
    Stores content hash so clients can skip re-download when unchanged.
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
    body = await request.body()
    # Enforce storage quota: server total and per-user limit (account for overwrite)
    old_size = 0
    if target.exists() and target.is_file():
        try:
            old_size = target.stat().st_size
        except OSError:
            pass
    server_limit = get_server_storage_limit_bytes()
    user_limit = get_user_storage_limit_bytes(server_limit, current_user.storage_limit_bytes)
    if server_limit is not None:
        total_used = get_total_used_bytes()
        if total_used - old_size + len(body) > server_limit:
            raise HTTPException(
                status_code=507,  # Insufficient Storage
                detail="Server storage limit reached",
            )
    if user_limit is not None:
        current_user_used = get_user_used_bytes(current_user.email)
        if current_user_used - old_size + len(body) > user_limit:
            raise HTTPException(
                status_code=507,  # Insufficient Storage
                detail="Your storage limit has been reached",
            )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    content_hash = compute_hash(body)
    await set_hash(session, current_user.email, path_param, content_hash)
    if not target.exists():
        log.error("upload_file wrote but file missing: %s", target)
    else:
        log.info("upload_file user=%s path=%s size=%d resolved=%s", current_user.email, path_param, len(body), target)
    return {"path": path_param, "size": len(body), "hash": content_hash}


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
