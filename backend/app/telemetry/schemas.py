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


class DiagnosticEventItem(BaseModel):
    """Single diagnostic event submitted in a telemetry batch."""

    trace_id: Optional[str] = None
    created_at: Optional[datetime] = None
    client_type: str = Field("", max_length=32)
    device_name: str = Field("", max_length=128)
    level: str = Field("ERROR", max_length=16)
    category: str = Field("sync", max_length=64)
    error_code: str = Field("", max_length=64)
    message: str
    context_json: Optional[str] = None


class SyncSummaryItem(BaseModel):
    """Sync run summary submitted in a telemetry batch."""

    trace_id: str = Field(..., min_length=1, max_length=64)
    client_type: str = Field("", max_length=32)
    client_version: str = Field("", max_length=64)
    device_name: str = Field("", max_length=128)
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    status: str = Field("ok", max_length=16)
    files_scanned: int = 0
    files_uploaded: int = 0
    files_downloaded: int = 0
    failure_count: int = 0
    bytes_transferred: int = 0
    error_summary_json: Optional[str] = None


class TelemetryBatchRequest(BaseModel):
    """Batch payload containing diagnostic events and sync summaries."""

    events: list[DiagnosticEventItem] = Field(default_factory=list)
    summaries: list[SyncSummaryItem] = Field(default_factory=list)


class DiagnosticEventResponse(BaseModel):
    """Diagnostic event row returned to admins."""

    id: int
    trace_id: Optional[str] = None
    created_at: datetime
    user_email: Optional[str] = None
    client_type: str
    device_name: str
    level: str
    category: str
    error_code: str
    message: str
    context_json: Optional[str] = None


class SyncSummaryResponse(BaseModel):
    """Sync summary row returned to admins."""

    id: int
    trace_id: str
    user_email: str
    client_type: str
    client_version: str
    device_name: str
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    status: str
    files_scanned: int
    files_uploaded: int
    files_downloaded: int
    failure_count: int
    bytes_transferred: int
    error_summary_json: Optional[str] = None

