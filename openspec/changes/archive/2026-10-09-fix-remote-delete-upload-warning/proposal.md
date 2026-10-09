## Why

When a file is deleted on the remote server, the desktop client's sync engine successfully removes the file locally during the local deletion phase, but subsequently misidentifies the deleted file as a new local-only file and queues it in `to_upload`. During upload execution, the client finds that the file no longer exists on disk, logs it as a skipped upload, emits a false sync warning message, turns the tray icon amber with a warning status, and reports a failure in sync summary telemetry. Excluding files scheduled for local deletion from the upload candidate list eliminates this false warning and ensures clean bidirectional synchronization.

## What Changes

- Filter out paths marked for local deletion (`to_del_local_set`) when constructing the `to_upload` list in `client-tauri/src-tauri/src/sync.rs`.
- Add a regression unit test `delete_remote_then_sync_removes_locally_not_upload` in `sync.rs` verifying that files deleted remotely are neither retained nor scheduled for upload.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `desktop-client`: Require the desktop client synchronization engine to exclude remotely deleted files (scheduled for local deletion) from being scheduled for upload, avoiding false skipped upload warnings and erroneous failure statuses.

## Impact

- **Affected code**: `client-tauri/src-tauri/src/sync.rs`
- **APIs**: No API changes.
- **Dependencies**: No new dependencies.
- **Behavior**: Remote deletions now sync cleanly to desktop clients without triggering `SyncStatus::Warning`, false upload skip logs, or incrementing `failure_count` in telemetry summaries.
