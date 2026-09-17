"""Test brandybox-doctor CLI functionality and output formats."""

import io
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import pytest

from app.cli.doctor import generate_llm_prompt, show_summary, show_trace
from app.telemetry.models import ClientConnection, DiagnosticEvent, SyncSummary
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
async def test_doctor_cli_outputs(mock_no_smtp, session_factory):
    """Seed test data and verify show_summary, show_trace, and generate_llm_prompt."""
    async with session_factory() as session:
        await create_user(
            session,
            UserCreate(email="pi_doctor_user@example.com", first_name="Pi", last_name="Doc"),
            is_admin=False,
        )
        now = datetime.now(timezone.utc)
        conn = ClientConnection(
            user_email="pi_doctor_user@example.com",
            client_type="desktop-macos",
            client_version="1.3.2",
            last_seen_at=now,
            last_sync_at=now,
            last_sync_ok=False,
            backend_version_at_ping="0.1.0",
        )
        session.add(conn)

        summary = SyncSummary(
            trace_id="sync-doctor-001",
            user_email="pi_doctor_user@example.com",
            client_type="desktop-macos",
            client_version="1.3.2",
            device_name="MacBook-Pro-Pi",
            started_at=now - timedelta(minutes=5),
            completed_at=now - timedelta(minutes=4),
            duration_ms=60000,
            status="failed",
            files_scanned=50,
            files_uploaded=2,
            files_downloaded=0,
            failure_count=1,
            bytes_transferred=204800,
            error_summary_json='{"failed_files": ["huge_file.zip"]}',
        )
        session.add(summary)

        event = DiagnosticEvent(
            trace_id="sync-doctor-001",
            user_email="pi_doctor_user@example.com",
            client_type="desktop-macos",
            device_name="MacBook-Pro-Pi",
            level="ERROR",
            category="sync.upload",
            error_code="TIMEOUT_524",
            message="Upload timed out for huge_file.zip",
            context_json='{"file": "huge_file.zip", "size": 204800}',
        )
        session.add(event)
        await session.commit()

    # 1. Test show_summary
    f_sum = io.StringIO()
    with redirect_stdout(f_sum):
        await show_summary()
    out_sum = f_sum.getvalue()
    assert "BRANDYBOX SYSTEM DIAGNOSTICS" in out_sum
    assert "pi_doctor_user@example.com" in out_sum
    assert "TIMEOUT_524" in out_sum
    assert "sync-doctor-001" in out_sum

    # 2. Test show_trace
    f_trace = io.StringIO()
    with redirect_stdout(f_trace):
        await show_trace("sync-doctor-001")
    out_trace = f_trace.getvalue()
    assert "TRACE TIMELINE: sync-doctor-001" in out_trace
    assert "FAILED" in out_trace
    assert "TIMEOUT_524" in out_trace
    assert "huge_file.zip" in out_trace
    assert "Chronological Events:" in out_trace

    # 3. Test generate_llm_prompt with specific trace
    f_llm = io.StringIO()
    with redirect_stdout(f_llm):
        await generate_llm_prompt(trace_id="sync-doctor-001")
    out_llm = f_llm.getvalue()
    assert "# BrandyBox Diagnostic Incident Report & LLM Context" in out_llm
    assert "## 1. System Environment" in out_llm
    assert "## 2. Incident Summary" in out_llm
    assert "sync-doctor-001" in out_llm
    assert "TIMEOUT_524" in out_llm
    assert "## 5. Diagnostic Directive for AI Assistant" in out_llm

    # 4. Test generate_llm_prompt default (finds latest error)
    f_llm_auto = io.StringIO()
    with redirect_stdout(f_llm_auto):
        await generate_llm_prompt(trace_id=None)
    out_llm_auto = f_llm_auto.getvalue()
    assert "sync-doctor-001" in out_llm_auto
    assert "TIMEOUT_524" in out_llm_auto
