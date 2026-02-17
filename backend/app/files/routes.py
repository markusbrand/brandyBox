"""File API routes: list, upload, download, delete."""

import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.files.storage import delete_file as storage_delete_file
from app.files.storage import list_files_recursive, resolve_user_path, user_base_path
from app.limiter import limiter
from app.users.models import User

router = APIRouter(prefix="/api/files", tags=["files"])
log = logging.getLogger(__name__)


def _normalize_path_param(path: Optional[str]) -> str:
    """Normalize path from query string: + means space in application/x-www-form-urlencoded."""
    if not path:
        return path or ""
    return path.replace("+", " ")


@router.get("/list", response_model=List[dict])
@limiter.limit("60/minute")
async def list_files(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[dict]:
    """List all files for the current user (recursive, path + mtime)."""
    base = user_base_path(current_user.email)
    base.mkdir(parents=True, exist_ok=True)  # ensure user folder exists (e.g. /mnt/.../user@email)
    result = list_files_recursive(base)
    log.info("list_files user=%s count=%d", current_user.email, len(result))
    return result


@router.post("/upload")
@limiter.limit("120/minute")
async def upload_file(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Upload a file. Query param: path (relative path). Body: raw file bytes.
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
    target.parent.mkdir(parents=True, exist_ok=True)
    body = await request.body()
    target.write_bytes(body)
    if not target.exists():
        log.error("upload_file wrote but file missing: %s", target)
    else:
        log.info("upload_file user=%s path=%s size=%d resolved=%s", current_user.email, path_param, len(body), target)
    return {"path": path_param, "size": len(body)}


@router.get("/download")
@limiter.limit("120/minute")
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
@limiter.limit("120/minute")
async def delete_file(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
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
    log.info("delete_file user=%s path=%s", current_user.email, path_param)
    return {"path": path_param, "deleted": True}
