"""Pydantic schemas for client ping API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ClientPingRequest(BaseModel):
    """Report client version and optional last sync outcome."""

    client_type: str = Field(..., min_length=1, max_length=32)
    client_version: str = Field(..., min_length=1, max_length=64)
    last_sync_at: Optional[datetime] = None
    last_sync_ok: Optional[bool] = None


class ClientConnectionResponse(BaseModel):
    """Row returned to admins."""

    user_email: str
    client_type: str
    client_version: str
    last_seen_at: datetime
    last_sync_at: Optional[datetime] = None
    last_sync_ok: Optional[bool] = None
    backend_version_at_ping: Optional[str] = None


class ServerEventResponse(BaseModel):
    """Diagnostic event for admin UI."""

    id: int
    created_at: datetime
    level: str
    category: str
    message: str
    detail_json: Optional[str] = None
    user_email: Optional[str] = None
