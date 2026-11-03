## Why

In `client-tauri/src-tauri/src/sync.rs`, the desktop sync engine synchronizes file deletions by identifying files removed locally and deleting them from the remote server via `client.delete_file(path)`. If `client.delete_file(path)` returns an error (e.g. HTTP 403, 500, network disconnect), the loop records a `DiagnosticEventPayload` and immediately terminates `run_sync` by returning `Err(format!("Delete server {}: {}", path, e))`.

However, unlike the `list_files` error handler (which properly enqueues a `SyncSummaryPayload` with status `"failed"` and flushes the telemetry queue via `flush_telemetry_queue`), the `delete_file` error path:
1. Omits calling `enqueue_sync_summary`, meaning no `SyncSummary` entry is ever created or persisted for this failed synchronization run.
2. Omits calling `flush_telemetry_queue(client)`, leaving the queued `DiagnosticEvent` unflushed in the offline queue file.
3. Leaves server administrators and diagnostics tools (`brandybox doctor`) completely blind to the failed sync run in aggregate metrics and summary tables.

## What Changes

- In `client-tauri/src-tauri/src/sync.rs`, when `client.delete_file(path)` fails:
  - Enqueue a `SyncSummaryPayload` with `status: "failed"`, `failure_count: 1`, elapsed `duration_ms`, `files_scanned: (local_list.len() + remote_list.len()) as i64`, and an `error_summary_json` detailing the delete failure.
  - Call `flush_telemetry_queue(client)` before returning the error so that both the diagnostic event and the sync summary are sent to the backend immediately (or retained in the offline buffer if offline).
- Add regression unit test in `client-tauri/src-tauri/src/sync.rs` asserting that when server file deletion fails during synchronization, a `"failed"` `SyncSummaryPayload` is queued and telemetry flushing is triggered.

## Capabilities

### Modified Capabilities
- `desktop-client`: Require the desktop client synchronization engine to generate a failed `SyncSummaryPayload` and flush telemetry when a remote file deletion fails during a synchronization cycle.

## Impact

- **Affected code**: `client-tauri/src-tauri/src/sync.rs`
- **APIs**: No changes to API schemas; existing `/api/telemetry/events` payload is properly populated.
- **Dependencies**: No new dependencies.
- **Behavior**: Synchronization runs that fail during remote file deletion now reliably emit `SyncSummary` records with status `"failed"`, allowing server telemetry and `brandybox doctor` to reflect sync failures accurately.
