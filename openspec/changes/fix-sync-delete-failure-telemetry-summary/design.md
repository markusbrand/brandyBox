## Context

In Brandy Box desktop client, `run_sync` in `client-tauri/src-tauri/src/sync.rs` orchestrates the two-way sync loop between the local sync directory and the backend server.
Telemetry tracking is split into two models:
1. `DiagnosticEvent`: Granular diagnostic events detailing specific errors (e.g. `sync.list`, `sync.delete`, `sync.download`, `sync.upload`).
2. `SyncSummary`: Per-sync-cycle overview documenting `status` (`"ok"`, `"warning"`, `"failed"`), duration, file counts scanned/transferred, failure count, and error summary.

During `run_sync`:
- If `client.list_files()` fails (lines 283–316), both a `DiagnosticEvent` and a `SyncSummary` with `status: "failed"` are enqueued, and `flush_telemetry_queue(client)` is invoked before returning `Err(e)`.
- If sync finishes without early error (lines 728–744), a `SyncSummary` with `status: "ok"` or `"warning"` is enqueued and `flush_telemetry_queue(client)` is invoked.
- However, if `client.delete_file(path)` fails during remote deletion (lines 364–380), only a `DiagnosticEvent` was queued. `enqueue_sync_summary` and `flush_telemetry_queue` were omitted before returning `Err`.

## Goals / Non-Goals

**Goals:**
- Ensure that any early exit from `run_sync` due to remote deletion failure records a `SyncSummaryPayload` with `status: "failed"` and `failure_count: 1`.
- Ensure `flush_telemetry_queue(client)` is invoked prior to returning `Err` so telemetry is dispatched immediately or saved to the offline buffer.
- Add regression testing to verify that delete failure generates the expected summary and triggers telemetry queue flushing.

**Non-Goals:**
- Changing retry semantics of `ApiClient::delete_file`.
- Modifying how callers in `lib.rs` handle the returned `Err`.

## Decisions

### Decision 1: Populate `SyncSummaryPayload` on `delete_file` Failure
When `client.delete_file(path)` returns `Err(e)`:
- Create error message: `let err_msg = format!("Delete server {}: {}", path, e);`
- Enqueue diagnostic event (category `"sync.delete"`, error code from `classify_error(&e)`).
- Enqueue sync summary:
  - `trace_id`: `trace_id.clone()`
  - `client_type`: `config::get_client_type().to_string()`
  - `client_version`: `env!("CARGO_PKG_VERSION").to_string()`
  - `device_name`: `config::get_device_name()`
  - `started_at`: `started_at.clone()`
  - `completed_at`: `Some(chrono::Utc::now().to_rfc3339())`
  - `duration_ms`: `start_instant.elapsed().as_millis() as i64`
  - `status`: `"failed".to_string()`
  - `files_scanned`: `(local_list.len() + remote_list.len()) as i64`
  - `files_uploaded`: 0
  - `files_downloaded`: 0
  - `failure_count`: 1
  - `bytes_transferred`: 0
  - `error_summary_json`: `Some(serde_json::json!({ "error": err_msg }).to_string())`
- Call `let _ = flush_telemetry_queue(client);`
- Return `Err(err_msg)`

*Rationale*:
Mirrors the pattern established in `list_files` error handling and ensures symmetry across failure exit points.

## Risks / Trade-offs

- **[Risk]** If backend is unreachable, `flush_telemetry_queue` will fail.
  - **Mitigation**: `flush_telemetry_queue` already handles network failure gracefully by retaining items in the offline queue file on disk (`config::get_telemetry_queue_path()`) and logging a warning. The next sync attempt flushes them.
