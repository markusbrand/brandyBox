## Context

See `proposal.md` for motivation. Currently, `client-tauri` uses `tauri-plugin-log` to write text logs to OS-specific directories and sends a minimal `/api/clients/ping` payload (`last_sync_ok: bool`). On the server, `backend/app/telemetry/` contains a rudimentary `ServerEvent` model, but lacks client error ingestion, sync run summaries, correlation IDs, or inspection utilities for local SSH access on the Raspberry Pi.

## Goals / Non-Goals

**Goals:**
- Provide complete visibility into sync failures and performance across all clients.
- Enable end-to-end tracing by tying client sync runs to backend HTTP requests via correlation headers.
- Offer an ergonomic CLI (`brandybox-doctor`) on the Raspberry Pi for rapid inspection and LLM prompt generation.
- Offer a Web UI dashboard for non-SSH administrative monitoring and one-click diagnostic export.
- Buffer diagnostic data on the client so that offline failures are preserved and uploaded when connectivity resumes.

**Non-Goals:**
- Streaming high-frequency debug logs over the network (debug logs remain on the client's local disk).
- Setting up external SaaS telemetry platforms (e.g. Sentry, Datadog) — the system remains self-hosted on the Raspberry Pi.
- Real-time WebSocket streaming of logs (polling / batch upload on sync completion or failure is sufficient and lightweight).

## Decisions

### 1. Correlation Identifier: `X-Sync-ID` Header
- **Decision**: The client generates a unique `trace_id` formatted as `sync-<timestamp_ms>-<randhex>` at the start of each sync cycle. This value is included as an `X-Sync-ID` header on all API calls (chunk uploads, downloads, deletions, tree queries).
- **Backend Handling**: A Starlette/FastAPI middleware extracts `X-Sync-ID` and stores it in Python's `contextvars`. When logging or persisting server events, the active `trace_id` is automatically included.
- **Alternatives Considered**: 
  - Standard W3C `traceparent`: More complex than needed for a single client-to-server interaction.
  - No correlation header (timestamp matching): Error-prone with concurrent multi-device syncs and clock skew.

### 2. Telemetry Ingestion Schema & SQLite Storage
- **Decision**: Add two new tables in SQLite (`/data/brandybox.db`):
  - `sync_summaries`: `id`, `trace_id` (unique), `user_email`, `client_type`, `client_version`, `device_name`, `started_at`, `duration_ms`, `status` (ok, warning, failed), `files_scanned`, `files_uploaded`, `files_downloaded`, `failure_count`, `bytes_transferred`, `error_summary_json`.
  - `diagnostic_events`: `id`, `trace_id`, `created_at`, `user_email`, `client_type`, `device_name`, `level` (WARN, ERROR), `category` (e.g. `sync.upload`, `sync.auth`), `error_code` (e.g. `CLOUDFLARE_524`, `HASH_MISMATCH`, `IO_PERMISSION_DENIED`), `message`, `context_json`.
  - Retention: Re-use the existing `server_events_retention_days` setting (default 30 days) to prune records older than the threshold.
- **Alternatives Considered**:
  - Pure JSONL file storage: Harder to perform indexed lookups, filters, and client status joins in the Web UI.
  - Single combined table: Separating overall run summaries from fine-grained error events keeps queries fast and the UI cleanly organized.

### 3. Client Buffering & Ingestion Pipeline (`client-tauri`)
- **Decision**: In `client-tauri`, diagnostic events are queued in an in-memory buffer backed by a persistent spool file (`sync_telemetry_queue.json`).
  - When an error occurs or a sync run completes, the event/summary is added to the queue.
  - The queue attempts to flush to `POST /api/telemetry/events`.
  - If the request fails (e.g., offline or network timeout), the queue remains persisted on disk and retries during the next sync cycle or heartbeat.
  - Max queue size is bounded (e.g., 200 items) with drop-oldest policy to prevent unbounded memory/disk usage if offline for months.
- **Alternatives Considered**:
  - Synchronous blocking HTTP calls on error: Can hang or slow down client error recovery if network is degraded.

### 4. `brandybox-doctor` CLI
- **Decision**: Implement the tool in Python under `backend/app/cli/doctor.py`, exposed via `python -m app.cli.doctor` and aliased in the container or Docker wrapper script as `brandybox-doctor`.
  - Options:
    - `--summary`: ASCII health summary (active clients, sync status, disk usage, 24h error count).
    - `--trace <trace_id>`: Merges client events and server logs for that trace into an ordered timeline.
    - `--llm-prompt [--trace <trace_id> | --last-error]`: Generates a Markdown document including system specs, error payload, timeline, and an explicit analysis prompt for an LLM.
- **Alternatives Considered**:
  - Standalone Bash script: Less maintainable, lacks direct access to SQLAlchemy models and Pydantic schemas.

### 5. Web UI Diagnostics View
- **Decision**: Enhance `web/src/pages/SettingsPage.tsx` with a full-width Diagnostics Drawer or dedicated tab:
  - Client matrix table with color-coded health chips (`Synced`, `Warning`, `Error`, `Offline`).
  - Error logs table with search and filtering by client/user. Clicking a row opens a modal/drawer showing full JSON context.
  - A prominent "Copy LLM Context" button that generates the same Markdown format as the CLI tool and copies it to clipboard.

## Risks / Trade-offs

- **[Risk] Sensitive Information in Error Context**: Context payloads could inadvertently include confidential paths or file names.
  - *Mitigation*: Sanitize auth tokens and sensitive headers; only store relative paths from sync roots; restrict diagnostic endpoints strictly to authenticated admins.
- **[Risk] Telemetry Flooding under Network Outages**: A client experiencing a continuous error loop could generate excessive diagnostic events.
  - *Mitigation*: Rate limit client telemetry submissions at the API layer (e.g. 60 requests/min) and throttle client event emission per file failure.
- **[Risk] SQLite Write Contention on Raspberry Pi**: Concurrent uploads and telemetry writes on SQLite.
  - *Mitigation*: SQLite WAL mode is already enabled in BrandyBox; telemetry flushes happen in batches.

## Migration Plan

1. Backend migrations: Add tables `sync_summaries` and `diagnostic_events` via SQLAlchemy metadata.
2. Ingestion endpoint `POST /api/telemetry/events` added to `backend/app/telemetry/routes.py`.
3. CLI script `brandybox-doctor` added to container path.
4. Client updated with correlation headers, error event queue, and summary builder.
5. Web frontend updated with the new Diagnostics view.
