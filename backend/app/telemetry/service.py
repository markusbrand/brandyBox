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
from app.telemetry.models import ClientConnection, ServerEvent

log = logging.getLogger(__name__)


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
    settings = get_settings()
    days = settings.server_events_retention_days
    if days and days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        await session.execute(delete(ServerEvent).where(ServerEvent.created_at < cutoff))


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
