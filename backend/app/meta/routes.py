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
    # True when Google OAuth env is set; UI should hide "Sign in with Google" when False.
    google_signin_available: bool


@router.get("/version", response_model=VersionResponse)
@limiter.exempt
def api_version() -> VersionResponse:
    """Return server API version and minimum supported desktop client version."""
    s = get_settings()
    google_ok = bool(
        str(s.google_client_id or "").strip() and str(s.google_client_secret or "").strip()
    )
    return VersionResponse(
        api_version=s.api_version,
        min_supported_client_version=s.min_supported_client_version,
        google_signin_available=google_ok,
    )
