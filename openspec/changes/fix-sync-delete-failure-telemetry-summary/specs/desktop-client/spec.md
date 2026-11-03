## ADDED Requirements

### Requirement: Sync Summary Emission on Remote Deletion Failure
When the desktop client synchronization engine encounters an error while deleting a remote file on the server, it SHALL record a `SyncSummary` event with status `"failed"`, document the failure count, error summary, and scan metrics, and attempt to flush the telemetry queue before returning the error.

#### Scenario: Server file deletion returns an error
- **WHEN** a local file was deleted and scheduled for remote deletion via `client.delete_file(path)`, but the server request fails with an error (e.g. HTTP 403, 500, or network disconnect)
- **THEN** the sync engine records a `DiagnosticEvent` with category `"sync.delete"`, records a `SyncSummary` with `status: "failed"` and `failure_count: 1`, flushes the telemetry queue, and returns the error to the caller.
