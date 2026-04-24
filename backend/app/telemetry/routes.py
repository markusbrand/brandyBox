"""Client ping and admin diagnostics."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin, get_current_user
from app.config import get_settings
from app.db.session import get_db
from app.limiter import limiter
from app.telemetry.schemas import ClientConnectionResponse, ClientPingRequest, ServerEventResponse
from app.telemetry.service import list_client_connections, list_server_events, upsert_client_ping
from app.users.models import User

router = APIRouter(prefix="/api", tags=["telemetry"])


@router.post("/clients/ping", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("120/minute")
async def client_ping(
    request: Request,
    body: ClientPingRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Record or update this client's version and optional last sync status."""
    settings = get_settings()
    await upsert_client_ping(
        session,
        user_email=current_user.email,
        client_type=body.client_type,
        client_version=body.client_version,
        last_sync_at=body.last_sync_at,
        last_sync_ok=body.last_sync_ok,
        backend_version=settings.api_version,
    )


@router.get("/admin/clients", response_model=list[ClientConnectionResponse])
@limiter.limit("60/minute")
async def admin_list_clients(
    request: Request,
    current_user: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ClientConnectionResponse]:
    """List last-known client connections (admin only)."""
    rows = await list_client_connections(session)
    return [
        ClientConnectionResponse(
            user_email=r.user_email,
            client_type=r.client_type,
            client_version=r.client_version,
            last_seen_at=r.last_seen_at,
            last_sync_at=r.last_sync_at,
            last_sync_ok=r.last_sync_ok,
            backend_version_at_ping=r.backend_version_at_ping,
        )
        for r in rows
    ]


@router.get("/admin/events", response_model=list[ServerEventResponse])
@limiter.limit("60/minute")
async def admin_list_events(
    request: Request,
    current_user: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(100, ge=1, le=500),
) -> list[ServerEventResponse]:
    """Recent server diagnostic events (admin only)."""
    rows = await list_server_events(session, limit=limit)
    return [
        ServerEventResponse(
            id=r.id,
            created_at=r.created_at,
            level=r.level,
            category=r.category,
            message=r.message,
            detail_json=r.detail_json,
            user_email=r.user_email,
        )
        for r in rows
    ]
