"""CLI diagnostic inspector and LLM prompt generator for BrandyBox on Raspberry Pi."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import sys
from typing import Optional

from sqlalchemy import select

from app.config import get_settings
from app.db.session import get_session, init_db
from app.telemetry.models import ClientConnection, DiagnosticEvent, SyncSummary
from app.users.models import User  # noqa: F401



def format_bytes(size: float) -> str:
    """Format byte sizes in human-readable units."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size) < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


async def show_summary() -> None:
    """Display system and cross-client health overview."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    # 1. Server info & disk metrics
    print("==================================================")
    print("          BRANDYBOX SYSTEM DIAGNOSTICS            ")
    print("==================================================")
    print(f"Server API Version: {settings.api_version}")
    print(f"Timestamp (UTC):    {now.strftime('%Y-%m-%d %H:%M:%S')}")

    db_path = Path(settings.db_path)
    if db_path.exists():
        db_size = format_bytes(db_path.stat().st_size)
        print(f"Database:           {db_path} (OK, {db_size})")
    else:
        print(f"Database:           {db_path} (NOT FOUND)")

    storage_path = Path(settings.server_disk_path or settings.storage_base_path)
    if storage_path.exists():
        total, used, free = shutil.disk_usage(storage_path)
        pct = (used / total) * 100 if total > 0 else 0
        print(f"Storage Path:       {storage_path}")
        print(f"Disk Usage:         {format_bytes(used)} / {format_bytes(total)} ({pct:.1f}% used, {format_bytes(free)} free)")
    else:
        print(f"Storage Path:       {storage_path} (NOT FOUND)")

    # 2. Query clients & syncs
    async with get_session() as session:
        clients_res = await session.execute(
            select(ClientConnection).order_by(ClientConnection.last_seen_at.desc())
        )
        clients = list(clients_res.scalars().all())

        cutoff_24h = now - timedelta(hours=24)
        errors_res = await session.execute(
            select(DiagnosticEvent)
            .where(DiagnosticEvent.created_at >= cutoff_24h)
            .where(DiagnosticEvent.level == "ERROR")
            .order_by(DiagnosticEvent.created_at.desc())
        )
        recent_errors = list(errors_res.scalars().all())

        recent_summaries_res = await session.execute(
            select(SyncSummary)
            .order_by(SyncSummary.started_at.desc())
            .limit(10)
        )
        recent_summaries = list(recent_summaries_res.scalars().all())

    print("\n--------------------------------------------------")
    print(f"Active Client Connections ({len(clients)} registered):")
    if not clients:
        print("  No client connections recorded.")
    for c in clients:
        status_str = "OK" if c.last_sync_ok else ("ERROR" if c.last_sync_ok is False else "UNKNOWN")
        last_sync = c.last_sync_at.strftime("%Y-%m-%d %H:%M:%S") if c.last_sync_at else "Never"
        print(f"  • {c.user_email} [{c.client_type} v{c.client_version}]")
        print(f"    Last seen: {c.last_seen_at.strftime('%Y-%m-%d %H:%M:%S')} | Last sync: {last_sync} | Status: {status_str}")

    print("\n--------------------------------------------------")
    print(f"Errors in Past 24 Hours ({len(recent_errors)} total):")
    if not recent_errors:
        print("  ✓ No error events recorded in the past 24 hours.")
    else:
        for err in recent_errors[:10]:
            ts = err.created_at.strftime("%Y-%m-%d %H:%M:%S")
            print(f"  • [{ts}] [{err.error_code or 'ERROR'}] {err.message}")
            if err.trace_id:
                print(f"    Trace ID: {err.trace_id} (Client: {err.client_type} / {err.device_name})")

    print("\n--------------------------------------------------")
    print(f"Recent Sync Runs ({len(recent_summaries)} shown):")
    if not recent_summaries:
        print("  No sync run summaries recorded.")
    for s in recent_summaries:
        ts = s.started_at.strftime("%Y-%m-%d %H:%M:%S")
        print(f"  • [{ts}] {s.trace_id} -> {s.status.upper()} ({s.duration_ms}ms, {s.files_uploaded} up, {s.files_downloaded} down, {s.failure_count} fail)")
    print("==================================================")


async def show_trace(trace_id: str) -> None:
    """Display chronological timeline for a specific trace identifier."""
    print("==================================================")
    print(f"          TRACE TIMELINE: {trace_id}")
    print("==================================================")

    async with get_session() as session:
        sum_res = await session.execute(
            select(SyncSummary).where(SyncSummary.trace_id == trace_id)
        )
        summary = sum_res.scalar_one_or_none()

        evts_res = await session.execute(
            select(DiagnosticEvent)
            .where(DiagnosticEvent.trace_id == trace_id)
            .order_by(DiagnosticEvent.created_at.asc())
        )
        events = list(evts_res.scalars().all())

    if not summary and not events:
        print(f"No records found for trace ID: {trace_id}")
        return

    if summary:
        print(f"User:        {summary.user_email}")
        print(f"Client:      {summary.client_type} v{summary.client_version} ({summary.device_name})")
        print(f"Outcome:     {summary.status.upper()} (Duration: {summary.duration_ms}ms)")
        print(f"Transfer:    {summary.files_scanned} scanned, {summary.files_uploaded} up, {summary.files_downloaded} down, {summary.failure_count} failures, {format_bytes(summary.bytes_transferred)}")
        if summary.error_summary_json:
            print(f"Summary Err: {summary.error_summary_json}")
        print("--------------------------------------------------")

    print("Chronological Events:")
    timeline_items: list[tuple[datetime, str]] = []
    if summary:
        timeline_items.append((summary.started_at, f"[START] Sync cycle initiated (trace: {trace_id})"))
        if summary.completed_at:
            timeline_items.append((summary.completed_at, f"[END] Sync cycle completed with status '{summary.status}'"))

    for evt in events:
        ctx_str = f" | Context: {evt.context_json}" if evt.context_json else ""
        msg = f"[{evt.level}] [{evt.category}] [{evt.error_code or 'GENERIC'}] {evt.message}{ctx_str}"
        timeline_items.append((evt.created_at, msg))

    timeline_items.sort(key=lambda item: item[0])
    for ts, line in timeline_items:
        print(f"  [{ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] {line}")
    print("==================================================")


async def generate_llm_prompt(trace_id: Optional[str] = None) -> None:
    """Format diagnostic context into a structured Markdown prompt for LLM root-cause analysis."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    async with get_session() as session:
        target_event: Optional[DiagnosticEvent] = None
        target_summary: Optional[SyncSummary] = None

        if trace_id:
            sum_res = await session.execute(
                select(SyncSummary).where(SyncSummary.trace_id == trace_id)
            )
            target_summary = sum_res.scalar_one_or_none()
            evts_res = await session.execute(
                select(DiagnosticEvent)
                .where(DiagnosticEvent.trace_id == trace_id)
                .order_by(DiagnosticEvent.created_at.asc())
            )
            trace_events = list(evts_res.scalars().all())
            if trace_events:
                target_event = trace_events[0]
        else:
            # Find latest error event
            evts_res = await session.execute(
                select(DiagnosticEvent)
                .where(DiagnosticEvent.level == "ERROR")
                .order_by(DiagnosticEvent.created_at.desc())
                .limit(1)
            )
            target_event = evts_res.scalar_one_or_none()
            if target_event and target_event.trace_id:
                trace_id = target_event.trace_id
                sum_res = await session.execute(
                    select(SyncSummary).where(SyncSummary.trace_id == trace_id)
                )
                target_summary = sum_res.scalar_one_or_none()
                evts_sub = await session.execute(
                    select(DiagnosticEvent)
                    .where(DiagnosticEvent.trace_id == trace_id)
                    .order_by(DiagnosticEvent.created_at.asc())
                )
                trace_events = list(evts_sub.scalars().all())
            else:
                trace_events = [target_event] if target_event else []

    storage_path = Path(settings.server_disk_path or settings.storage_base_path)
    disk_info = "Unknown"
    if storage_path.exists():
        total, used, free = shutil.disk_usage(storage_path)
        disk_info = f"{format_bytes(used)} used / {format_bytes(total)} total ({format_bytes(free)} free)"

    print("# BrandyBox Diagnostic Incident Report & LLM Context")
    print("\n## 1. System Environment")
    print(f"- **Backend API Version**: `{settings.api_version}`")
    print(f"- **Server Timestamp**: `{now.strftime('%Y-%m-%d %H:%M:%S UTC')}`")
    print(f"- **Storage Disk Status**: `{disk_info}`")
    print("- **Database**: `SQLite`")

    print("\n## 2. Incident Summary")
    if target_summary:
        print(f"- **Trace ID**: `{target_summary.trace_id}`")
        print(f"- **User**: `{target_summary.user_email}`")
        print(f"- **Client**: `{target_summary.client_type}` (v`{target_summary.client_version}`) on `{target_summary.device_name}`")
        print(f"- **Sync Outcome**: `{target_summary.status}` ({target_summary.failure_count} failures, duration {target_summary.duration_ms}ms)")
        print(f"- **Files Processed**: {target_summary.files_scanned} scanned, {target_summary.files_uploaded} uploaded, {target_summary.files_downloaded} downloaded")
    elif target_event:
        print(f"- **Trace ID**: `{target_event.trace_id or 'N/A'}`")
        print(f"- **User**: `{target_event.user_email or 'N/A'}`")
        print(f"- **Client**: `{target_event.client_type}` on `{target_event.device_name}`")
        print(f"- **Error Level**: `{target_event.level}`")
    else:
        print("No error events or sync summaries available.")

    print("\n## 3. Failure Details & Diagnostics")
    if target_event:
        print(f"- **Category**: `{target_event.category}`")
        print(f"- **Error Code**: `{target_event.error_code or 'UNKNOWN'}`")
        print(f"- **Message**: {target_event.message}")
        if target_event.context_json:
            print("- **Structured Context**:")
            try:
                parsed_ctx = json.loads(target_event.context_json)
                formatted_ctx = json.dumps(parsed_ctx, indent=2)
            except Exception:
                formatted_ctx = target_event.context_json
            print(f"```json\n{formatted_ctx}\n```")
    else:
        print("No specific error event recorded.")

    print("\n## 4. Correlated Event Timeline")
    timeline_items: list[tuple[datetime, str]] = []
    if target_summary:
        timeline_items.append((target_summary.started_at, f"Sync cycle started (trace: `{target_summary.trace_id}`)"))
        if target_summary.completed_at:
            timeline_items.append((target_summary.completed_at, f"Sync cycle finished with status `{target_summary.status}`"))

    for evt in trace_events:
        ctx_detail = f" (Context: {evt.context_json})" if evt.context_json else ""
        timeline_items.append((evt.created_at, f"[{evt.level}] {evt.message}{ctx_detail}"))

    timeline_items.sort(key=lambda item: item[0])
    if not timeline_items:
        print("No timeline steps available.")
    else:
        for i, (ts, item) in enumerate(timeline_items, 1):
            print(f"{i}. `{ts.strftime('%Y-%m-%d %H:%M:%S')}` - {item}")

    print("\n## 5. Diagnostic Directive for AI Assistant")
    print(
        "Please analyze the synchronization failure recorded above. Identify the probable root cause "
        "(e.g., Cloudflare timeout, HTTP 524, SQLite disk lock, chunk sha256 mismatch, file permission error, "
        "or offline disconnect). Provide actionable steps to resolve the issue both for client retry logic "
        "and server host configuration."
    )


async def main_async() -> None:
    parser = argparse.ArgumentParser(description="BrandyBox Raspberry Pi Diagnostic Tool")
    parser.add_argument("--summary", action="store_true", help="Display system & client health summary")
    parser.add_argument("--trace", type=str, help="Display chronological timeline for given trace ID")
    parser.add_argument("--llm-prompt", dest="llm_prompt", action="store_true", help="Generate LLM-ready markdown diagnostic prompt")
    parser.add_argument("--last-error", action="store_true", help="Target most recent error for --llm-prompt")

    args = parser.parse_args()

    try:
        await init_db()
    except Exception as e:
        print(f"[init_db warning]: {e}", file=sys.stderr)



    if args.llm_prompt:
        await generate_llm_prompt(trace_id=args.trace)
    elif args.trace:
        await show_trace(args.trace)
    elif args.summary:
        await show_summary()
    else:
        # Default to summary if no args provided
        await show_summary()



def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
