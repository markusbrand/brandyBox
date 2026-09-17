"""Tests for telemetry database models and retention cleanup."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select

from app.telemetry.models import DiagnosticEvent, SyncSummary
from app.telemetry.service import prune_telemetry_records
from app.users.models import UserCreate
from app.users.service import create_user


@pytest.fixture
def mock_no_smtp(monkeypatch):
    from app.users import service as svc
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.smtp_host = ""
    mock.smtp_from = ""
    monkeypatch.setattr(svc, "get_settings", lambda: mock)


@pytest.mark.asyncio
async def test_sync_summary_and_diagnostic_event_crud_and_pruning(mock_no_smtp, session_factory):
    async with session_factory() as session:
        # Create test user
        user, _ = await create_user(
            session,
            UserCreate(email="telemetry_test@example.com", first_name="Telem", last_name="Tester"),
            is_admin=False,
        )
        await session.commit()

    async with session_factory() as session:
        # Create sync summary
        now = datetime.now(timezone.utc)
        summary = SyncSummary(
            trace_id="sync-123456-abcdef",
            user_email="telemetry_test@example.com",
            client_type="desktop-macos",
            client_version="1.3.2",
            device_name="Markus-MacBook",
            started_at=now - timedelta(seconds=12),
            completed_at=now,
            duration_ms=12000,
            status="warning",
            files_scanned=150,
            files_uploaded=10,
            files_downloaded=5,
            failure_count=1,
            bytes_transferred=102400,
            error_summary_json='{"errors": ["Upload timeout for file.txt"]}',
        )
        session.add(summary)

        # Create diagnostic events
        event = DiagnosticEvent(
            trace_id="sync-123456-abcdef",
            user_email="telemetry_test@example.com",
            client_type="desktop-macos",
            device_name="Markus-MacBook",
            level="ERROR",
            category="sync.upload",
            error_code="UPLOAD_TIMEOUT",
            message="Upload timed out after 30s",
            context_json='{"path": "file.txt", "chunk_index": 0}',
        )
        session.add(event)
        await session.commit()

    async with session_factory() as session:
        res_summary = await session.execute(
            select(SyncSummary).where(SyncSummary.trace_id == "sync-123456-abcdef")
        )
        saved_summary = res_summary.scalar_one_or_none()
        assert saved_summary is not None
        assert saved_summary.status == "warning"
        assert saved_summary.files_uploaded == 10
        assert saved_summary.failure_count == 1

        res_event = await session.execute(
            select(DiagnosticEvent).where(DiagnosticEvent.trace_id == "sync-123456-abcdef")
        )
        saved_event = res_event.scalar_one_or_none()
        assert saved_event is not None
        assert saved_event.error_code == "UPLOAD_TIMEOUT"
        assert saved_event.level == "ERROR"

    # Now test retention pruning:
    async with session_factory() as session:
        # Add old records (40 days old)
        old_time = datetime.now(timezone.utc) - timedelta(days=40)
        old_summary = SyncSummary(
            trace_id="sync-old-999999",
            user_email="telemetry_test@example.com",
            client_type="desktop-macos",
            client_version="1.0.0",
            device_name="Old-Device",
            started_at=old_time,
            completed_at=old_time,
            duration_ms=1000,
            status="ok",
        )
        old_event = DiagnosticEvent(
            trace_id="sync-old-999999",
            created_at=old_time,
            user_email="telemetry_test@example.com",
            client_type="desktop-macos",
            device_name="Old-Device",
            level="WARN",
            category="sync",
            message="Old warning",
        )
        session.add(old_summary)
        session.add(old_event)
        await session.commit()

    async with session_factory() as session:
        # Prune with 30 days retention
        await prune_telemetry_records(session, retention_days=30)
        await session.commit()

    async with session_factory() as session:
        # Check old records were deleted
        old_s = await session.execute(select(SyncSummary).where(SyncSummary.trace_id == "sync-old-999999"))
        assert old_s.scalar_one_or_none() is None

        old_e = await session.execute(select(DiagnosticEvent).where(DiagnosticEvent.trace_id == "sync-old-999999"))
        assert old_e.scalar_one_or_none() is None

        # Check new records still exist
        new_s = await session.execute(select(SyncSummary).where(SyncSummary.trace_id == "sync-123456-abcdef"))
        assert new_s.scalar_one_or_none() is not None


def test_telemetry_api_routes(client):
    """Verify POST /api/telemetry/events and GET /api/admin/telemetry/* endpoints."""
    # 1. Login as admin
    login_r = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpass123"},
    )
    assert login_r.status_code == 200
    token = login_r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ingest telemetry batch
    payload = {
        "events": [
            {
                "trace_id": "sync-api-test-01",
                "client_type": "desktop-macos",
                "device_name": "TestMac",
                "level": "ERROR",
                "category": "sync.network",
                "error_code": "CLOUDFLARE_524",
                "message": "Gateway timeout during chunk upload",
                "context_json": '{"chunk": 2, "file": "video.mp4"}',
            }
        ],
        "summaries": [
            {
                "trace_id": "sync-api-test-01",
                "client_type": "desktop-macos",
                "client_version": "1.3.2",
                "device_name": "TestMac",
                "started_at": "2026-09-16T21:00:00Z",
                "completed_at": "2026-09-16T21:01:00Z",
                "duration_ms": 60000,
                "status": "failed",
                "files_scanned": 100,
                "files_uploaded": 1,
                "files_downloaded": 0,
                "failure_count": 1,
                "bytes_transferred": 5000000,
                "error_summary_json": '{"failed_files": ["video.mp4"]}',
            }
        ],
    }
    ingest_res = client.post("/api/telemetry/events", json=payload, headers=headers)
    assert ingest_res.status_code == 204

    # 3. Query admin summaries
    sum_res = client.get("/api/admin/telemetry/summaries", headers=headers)
    assert sum_res.status_code == 200
    summaries = sum_res.json()
    assert any(s["trace_id"] == "sync-api-test-01" for s in summaries)
    target_summary = next(s for s in summaries if s["trace_id"] == "sync-api-test-01")
    assert target_summary["status"] == "failed"
    assert target_summary["failure_count"] == 1
    assert target_summary["user_email"] == "test@example.com"

    # Filter summaries by status
    sum_res_filtered = client.get("/api/admin/telemetry/summaries?status=failed", headers=headers)
    assert sum_res_filtered.status_code == 200
    assert all(s["status"] == "failed" for s in sum_res_filtered.json())

    # 4. Query admin events
    evt_res = client.get("/api/admin/telemetry/events", headers=headers)
    assert evt_res.status_code == 200
    events = evt_res.json()
    assert any(e["trace_id"] == "sync-api-test-01" for e in events)
    target_evt = next(e for e in events if e["trace_id"] == "sync-api-test-01")
    assert target_evt["error_code"] == "CLOUDFLARE_524"
    assert target_evt["level"] == "ERROR"

    # Filter events by trace_id
    evt_res_filtered = client.get("/api/admin/telemetry/events?trace_id=sync-api-test-01", headers=headers)
    assert evt_res_filtered.status_code == 200
    assert len(evt_res_filtered.json()) >= 1
    assert evt_res_filtered.json()[0]["trace_id"] == "sync-api-test-01"

