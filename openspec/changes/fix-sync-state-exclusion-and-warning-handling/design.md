## Context

The desktop client synchronization engine (`sync.rs`) maintains `sync_state.json` (`state.paths`), which serves as the base set of previously synchronized files (`last_synced`). This set is critical for bidirectional sync: when a file disappears locally, it is compared against `last_synced` to determine if it should be deleted from the server; similarly, if a file disappears from the server, it is compared against `last_synced` to delete it locally.

In the current implementation, `base_synced` is computed as `remaining_local.intersection(&remaining_remote)` before file transfers occur, without removing files that are scheduled for transfer (`to_download` and `to_upload`). Consequently, when a transfer fails or is skipped, the file is already contained in `base_synced`, causing `persist_current_state` to erroneously write the file into `state.paths`.

Furthermore, when transfers are skipped, `sync.rs` transitions to `SyncStatus::Warning(msg)`. The React settings UI listens for `sync-status` events, but only checks for `"synced"` and `"error"`, failing to clear the syncing state or display the warning.

Finally, the `run_sync` command in `lib.rs` spawns an asynchronous sync thread unconditionally, creating a race condition if background sync is already executing.

## Goals / Non-Goals

**Goals:**
- Ensure that only files verified as identical or whose transfer succeeded are persisted in `state.paths` (`sync_state.json`).
- Ensure that `SyncStatus::Warning` events properly reset the settings UI syncing state, re-enable manual sync, refresh settings, and display the warning banner.
- Guard `run_sync` against concurrent executions.
- Maintain backwards compatibility and verify with regression unit tests.

**Non-Goals:**
- Redesigning the entire bidirectional sync algorithm or switching to conflict-branch file versioning.
- Altering the backend API endpoints or SQLite storage schema.

## Decisions

### 1. Compute `base_synced` excluding pending transfers
In `client-tauri/src-tauri/src/sync.rs`, compute `base_synced` after determining `to_download` and `to_upload`:
```rust
let to_download_set: HashSet<String> = to_download.iter().cloned().collect();
let to_upload_set: HashSet<String> = to_upload.iter().cloned().collect();
let base_synced: HashSet<String> = remaining_local
    .intersection(&remaining_remote)
    .filter(|p| !is_ignored(p) && !to_download_set.contains(p.as_str()) && !to_upload_set.contains(p.as_str()))
    .cloned()
    .collect();
```
*Rationale*: Files that need download or upload are not in sync at the start of the cycle. They only become in sync if their respective transfer completes successfully (`completed_downloads` or `completed_uploads`). Any file whose transfer fails or is skipped will not be in `base_synced`, `completed_downloads`, or `completed_uploads`, thereby guaranteeing it is excluded from `state.paths`.

### 2. Handle `"warning"` status in Settings.tsx
In `client-tauri/src/Settings.tsx`, update the `"sync-status"` listener:
```typescript
const unlistenPromise = listen<{ status: string; message?: string | null }>("sync-status", (event) => {
  const { status, message } = event.payload;
  if (status === "synced" || status === "warning" || status === "error") {
    setSyncing(false);
    setSyncProgress(null);
    if (status === "error" && message) setSyncError(message);
    if (status === "warning" && message) setSyncWarning(message);
    if (status === "synced" || status === "warning") loadSettings();
  }
});
```
Also add a `syncWarning` state to render an `<Alert severity="warning">` component.

### 3. Add concurrency guard to `run_sync`
In `client-tauri/src-tauri/src/lib.rs`:
```rust
#[tauri::command]
fn run_sync(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    if !config::user_has_set_sync_folder() {
        return Err("Sync folder not set".to_string());
    }
    let (current_status, _) = sync::get_sync_status();
    if current_status == "syncing" {
        return Ok(serde_json::json!({ "started": false, "message": "Sync already in progress" }));
    }
    ...
```

## Risks / Trade-offs

- **[Risk]** If a file has transfer failures across multiple cycles, will it be uploaded or downloaded again next time?
  - *Mitigation*: Yes, because it is excluded from `state.paths`, the diffing engine will re-evaluate it against remote mtime and hash, naturally retrying the transfer on the subsequent sync cycle.
- **[Risk]** What if `status` was set to `"syncing"` from a dead thread?
  - *Mitigation*: Sync runs inside a thread with panic handlers and standard Result returns; on completion it always sets either `Synced`, `Warning`, or `Error`.
