"""Public API metadata."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.limiter import limiter

router = APIRouter(prefix="/api/meta", tags=["meta"])


class VersionResponse(BaseModel):
    """Backend and client compatibility hints."""

    api_version: str
    min_supported_client_version: str


@router.get("/version", response_model=VersionResponse)
@limiter.exempt
def api_version() -> VersionResponse:
    """Return server API version and minimum supported desktop client version."""
    s = get_settings()
    return VersionResponse(
        api_version=s.api_version,
        min_supported_client_version=s.min_supported_client_version,
    )
