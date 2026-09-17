"""Context variable and logging filter for X-Sync-ID trace correlation."""

from contextvars import ContextVar
import logging
from typing import Optional

trace_id_ctx: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


def get_current_trace_id() -> Optional[str]:
    """Retrieve the active trace / sync correlation ID for this request/task."""
    return trace_id_ctx.get()


def set_current_trace_id(trace_id: Optional[str]):
    """Set the active trace ID."""
    return trace_id_ctx.set(trace_id)


class TraceIdFilter(logging.Filter):
    """Injects [trace_id] into log records when available."""

    def filter(self, record: logging.LogRecord) -> bool:
        tid = get_current_trace_id()
        record.trace_id = f" [{tid}]" if tid else ""
        return True
