"""Persist client pings and server events."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.telemetry.models import ClientConnection, DiagnosticEvent, ServerEvent, SyncSummary

log = logging.getLogger(__name__)


async def prune_telemetry_records(session: AsyncSession, retention_days: Optional[int] = None) -> None:
    """Prune ServerEvent, DiagnosticEvent, and SyncSummary records older than retention threshold."""
    settings = get_settings()
    days = retention_days if retention_days is not None else settings.server_events_retention_days
    if days and days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        await session.execute(delete(ServerEvent).where(ServerEvent.created_at < cutoff))
        await session.execute(delete(DiagnosticEvent).where(DiagnosticEvent.created_at < cutoff))
        await session.execute(delete(SyncSummary).where(SyncSummary.started_at < cutoff))


async def log_server_event(
    session: AsyncSession,
    *,
    level: str,
    category: str,
    message: str,
    detail: Optional[dict[str, Any]] = None,
    user_email: Optional[str] = None,
) -> None:
    """Append a server event and occasionally prune old rows."""
    row = ServerEvent(
        level=level[:16],
        category=category[:64],
        message=message,
        detail_json=json.dumps(detail) if detail else None,
        user_email=user_email,
    )
    session.add(row)
    await session.flush()
    await prune_telemetry_records(session)



async def upsert_client_ping(
    session: AsyncSession,
    *,
    user_email: str,
    client_type: str,
    client_version: str,
    last_sync_at: Optional[datetime],
    last_sync_ok: Optional[bool],
    backend_version: str,
) -> None:
    """Insert or update client_connections for (user_email, client_type)."""
    # ⚡ Bolt: Use SQLite ON CONFLICT DO UPDATE to replace SELECT + INSERT/UPDATE with a single UPSERT query.
    # Impact: Reduces database roundtrips from 2 to 1 per client ping, avoiding N+1 query overhead for concurrent clients.
    now = datetime.now(timezone.utc)
    ct = client_type[:32]
    cv = client_version[:64]
    bv = backend_version[:32]

    stmt = insert(ClientConnection).values(
        user_email=user_email,
        client_type=ct,
        client_version=cv,
        last_seen_at=now,
        last_sync_at=last_sync_at,
        last_sync_ok=last_sync_ok,
        backend_version_at_ping=bv,
    )

    stmt = stmt.on_conflict_do_update(
        index_elements=['user_email', 'client_type'],
        set_=dict(
            client_version=stmt.excluded.client_version,
            last_seen_at=stmt.excluded.last_seen_at,
            last_sync_at=stmt.excluded.last_sync_at,
            last_sync_ok=stmt.excluded.last_sync_ok,
            backend_version_at_ping=stmt.excluded.backend_version_at_ping,
        )
    )

    await session.execute(stmt)
    await session.flush()
    log.debug(
        "Client ping user=%s type=%s version=%s sync_ok=%s",
        user_email,
        ct,
        cv,
        last_sync_ok,
    )


async def list_client_connections(session: AsyncSession) -> list[ClientConnection]:
    """All client connection rows (admin)."""
    result = await session.execute(select(ClientConnection).order_by(ClientConnection.last_seen_at.desc()))
    return list(result.scalars().all())


async def list_server_events(session: AsyncSession, limit: int = 100) -> list[ServerEvent]:
    """Recent server events (admin), newest first."""
    lim = max(1, min(limit, 500))
    result = await session.execute(select(ServerEvent).order_by(ServerEvent.id.desc()).limit(lim))
    return list(result.scalars().all())


async def ingest_telemetry_batch(
    session: AsyncSession,
    *,
    user_email: str,
    events: list[Any],
    summaries: list[Any],
) -> None:
    """Persist batch of diagnostic events and sync summaries reported by a client."""
    now = datetime.now(timezone.utc)
    for evt in events:
        row = DiagnosticEvent(
            trace_id=evt.trace_id,
            created_at=evt.created_at or now,
            user_email=user_email,
            client_type=evt.client_type[:32] if evt.client_type else "",
            device_name=evt.device_name[:128] if evt.device_name else "",
            level=evt.level[:16] if evt.level else "ERROR",
            category=evt.category[:64] if evt.category else "sync",
            error_code=evt.error_code[:64] if evt.error_code else "",
            message=evt.message,
            context_json=evt.context_json,
        )
        session.add(row)

    for sm in summaries:
        stmt = insert(SyncSummary).values(
            trace_id=sm.trace_id[:64],
            user_email=user_email,
            client_type=sm.client_type[:32] if sm.client_type else "",
            client_version=sm.client_version[:64] if sm.client_version else "",
            device_name=sm.device_name[:128] if sm.device_name else "",
            started_at=sm.started_at,
            completed_at=sm.completed_at or now,
            duration_ms=sm.duration_ms,
            status=sm.status[:16] if sm.status else "ok",
            files_scanned=sm.files_scanned,
            files_uploaded=sm.files_uploaded,
            files_downloaded=sm.files_downloaded,
            failure_count=sm.failure_count,
            bytes_transferred=sm.bytes_transferred,
            error_summary_json=sm.error_summary_json,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["trace_id"],
            set_=dict(
                client_type=stmt.excluded.client_type,
                client_version=stmt.excluded.client_version,
                device_name=stmt.excluded.device_name,
                completed_at=stmt.excluded.completed_at,
                duration_ms=stmt.excluded.duration_ms,
                status=stmt.excluded.status,
                files_scanned=stmt.excluded.files_scanned,
                files_uploaded=stmt.excluded.files_uploaded,
                files_downloaded=stmt.excluded.files_downloaded,
                failure_count=stmt.excluded.failure_count,
                bytes_transferred=stmt.excluded.bytes_transferred,
                error_summary_json=stmt.excluded.error_summary_json,
            ),
        )
        await session.execute(stmt)

    await session.flush()
    await prune_telemetry_records(session)


async def list_sync_summaries(
    session: AsyncSession,
    *,
    limit: int = 100,
    user_email: Optional[str] = None,
    status: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> list[SyncSummary]:
    """List sync summaries, newest first."""
    lim = max(1, min(limit, 500))
    query = select(SyncSummary)
    if user_email:
        query = query.where(SyncSummary.user_email == user_email)
    if status:
        query = query.where(SyncSummary.status == status)
    if trace_id:
        query = query.where(SyncSummary.trace_id == trace_id)
    query = query.order_by(SyncSummary.started_at.desc()).limit(lim)
    result = await session.execute(query)
    return list(result.scalars().all())


async def list_diagnostic_events(
    session: AsyncSession,
    *,
    limit: int = 100,
    trace_id: Optional[str] = None,
    level: Optional[str] = None,
    category: Optional[str] = None,
    user_email: Optional[str] = None,
) -> list[DiagnosticEvent]:
    """List diagnostic events, newest first."""
    lim = max(1, min(limit, 500))
    query = select(DiagnosticEvent)
    if trace_id:
        query = query.where(DiagnosticEvent.trace_id == trace_id)
    if level:
        query = query.where(DiagnosticEvent.level == level)
    if category:
        query = query.where(DiagnosticEvent.category == category)
    if user_email:
        query = query.where(DiagnosticEvent.user_email == user_email)
    query = query.order_by(DiagnosticEvent.id.desc()).limit(lim)
    result = await session.execute(query)
    return list(result.scalars().all())

