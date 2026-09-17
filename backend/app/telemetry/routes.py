"""Client ping and admin diagnostics."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin, get_current_user
from app.config import get_settings
from app.db.session import get_db
from app.limiter import limiter
from app.telemetry.schemas import (
    ClientConnectionResponse,
    ClientPingRequest,
    DiagnosticEventResponse,
    ServerEventResponse,
    SyncSummaryResponse,
    TelemetryBatchRequest,
)
from app.telemetry.service import (
    ingest_telemetry_batch,
    list_client_connections,
    list_diagnostic_events,
    list_server_events,
    list_sync_summaries,
    upsert_client_ping,
)
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


@router.post("/telemetry/events", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("120/minute")
async def ingest_telemetry(
    request: Request,
    body: TelemetryBatchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Ingest a batch of diagnostic events and sync summaries from a client."""
    await ingest_telemetry_batch(
        session,
        user_email=current_user.email,
        events=body.events,
        summaries=body.summaries,
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


@router.get("/admin/telemetry/summaries", response_model=list[SyncSummaryResponse])
@limiter.limit("60/minute")
async def admin_list_summaries(
    request: Request,
    current_user: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(100, ge=1, le=500),
    user_email: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    trace_id: Optional[str] = Query(None),
) -> list[SyncSummaryResponse]:
    """Query sync run summaries (admin only)."""
    rows = await list_sync_summaries(
        session,
        limit=limit,
        user_email=user_email,
        status=status,
        trace_id=trace_id,
    )
    return [
        SyncSummaryResponse(
            id=r.id,
            trace_id=r.trace_id,
            user_email=r.user_email,
            client_type=r.client_type,
            client_version=r.client_version,
            device_name=r.device_name,
            started_at=r.started_at,
            completed_at=r.completed_at,
            duration_ms=r.duration_ms,
            status=r.status,
            files_scanned=r.files_scanned,
            files_uploaded=r.files_uploaded,
            files_downloaded=r.files_downloaded,
            failure_count=r.failure_count,
            bytes_transferred=r.bytes_transferred,
            error_summary_json=r.error_summary_json,
        )
        for r in rows
    ]


@router.get("/admin/telemetry/events", response_model=list[DiagnosticEventResponse])
@limiter.limit("60/minute")
async def admin_list_telemetry_events(
    request: Request,
    current_user: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(100, ge=1, le=500),
    trace_id: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    user_email: Optional[str] = Query(None),
) -> list[DiagnosticEventResponse]:
    """Query client diagnostic events (admin only)."""
    rows = await list_diagnostic_events(
        session,
        limit=limit,
        trace_id=trace_id,
        level=level,
        category=category,
        user_email=user_email,
    )
    return [
        DiagnosticEventResponse(
            id=r.id,
            trace_id=r.trace_id,
            created_at=r.created_at,
            user_email=r.user_email,
            client_type=r.client_type,
            device_name=r.device_name,
            level=r.level,
            category=r.category,
            error_code=r.error_code,
            message=r.message,
            context_json=r.context_json,
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

