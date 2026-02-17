"""File API routes: list, upload, download."""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.files.storage import list_files_recursive, resolve_user_path, user_base_path
from app.limiter import limiter
from app.users.models import User

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/list", response_model=List[dict])
@limiter.limit("60/minute")
async def list_files(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[dict]:
    """List all files for the current user (recursive, path + mtime)."""
    base = user_base_path(current_user.email)
    if not base.exists():
        return []
    return list_files_recursive(base)


@router.post("/upload")
@limiter.limit("120/minute")
async def upload_file(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Upload a file. Query param: path (relative path). Body: raw file bytes.
    """
    path_param = request.query_params.get("path")
    if not path_param or not path_param.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'path' is required",
        )
    try:
        target = resolve_user_path(current_user.email, path_param)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    body = await request.body()
    target.write_bytes(body)
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
    path_param = request.query_params.get("path")
    if not path_param or not path_param.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'path' is required",
        )
    try:
        target = resolve_user_path(current_user.email, path_param)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    if not target.exists() or not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    return FileResponse(
        path=target,
        filename=target.name,
        media_type="application/octet-stream",
    )
