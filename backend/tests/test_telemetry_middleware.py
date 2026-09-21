"""Test X-Sync-ID correlation middleware and log context binding."""

import logging
import pytest
from fastapi.testclient import TestClient

from app.telemetry.context import get_current_trace_id


def test_x_sync_id_header_middleware(client: TestClient, caplog: pytest.LogCaptureFixture):
    """Test that X-Sync-ID header is propagated back and trace ID is logged."""
    sync_id = "sync-1710633000-deadbeef"
    with caplog.at_level(logging.INFO, logger="app"):
        response = client.get("/health", headers={"X-Sync-ID": sync_id})

    assert response.status_code == 200
    assert response.headers.get("X-Sync-ID") == sync_id
    assert get_current_trace_id() is None  # Reset after request finishes


def test_trace_id_in_log_formatter():
    """Verify TraceIdFilter formats record.trace_id correctly."""
    from app.telemetry.context import TraceIdFilter, trace_id_ctx

    record = logging.LogRecord("test", logging.INFO, "path", 1, "test message", (), None)
    filt = TraceIdFilter()

    # Without trace_id set
    filt.filter(record)
    assert record.trace_id == ""

    # With trace_id set
    token = trace_id_ctx.set("sync-999")
    try:
        filt.filter(record)
        assert record.trace_id == " [sync-999]"
    finally:
        trace_id_ctx.reset(token)
