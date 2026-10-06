## Why

When a file transfer (download or upload) for an existing file fails or is skipped during synchronization, the desktop client's sync engine mistakenly includes the file in `base_synced` and saves it into `state.paths` (`sync_state.json`), falsely marking the file as synchronized. Furthermore, when the synchronization engine completes with a `SyncStatus::Warning`, the desktop client settings UI ignores the `"warning"` status event, leaving the "Sync now" button disabled with an infinite loading spinner and failing to display the warning message. Finally, the Tauri `run_sync` command does not guard against concurrent sync execution, allowing overlapping sync processes when manual sync is triggered.

## What Changes

- In `client-tauri/src-tauri/src/sync.rs`, filter out files scheduled for transfer (`to_download` and `to_upload`) when constructing `base_synced`, ensuring only files that are verified identical and require no transfer are considered base synced. Files with skipped or failed transfers are therefore properly excluded from `state.paths` (`sync_state.json`).
- In `client-tauri/src/Settings.tsx`, handle the `warning` sync status in the event listener by resetting `syncing` to `false`, clearing `syncProgress`, reloading settings, and displaying the warning banner.
- In `client-tauri/src-tauri/src/lib.rs`, guard the `run_sync` command by checking if synchronization is already in progress (`status == "syncing"`), returning early instead of launching overlapping sync threads.
- Add regression tests in `client-tauri/src-tauri/src/sync.rs` verifying that skipped/failed downloads and uploads of existing files are excluded from `state.paths`.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `desktop-client`: Require the desktop client synchronization engine to exclude skipped or failed file transfers from the persistent synced state (`sync_state.json`), properly handle and display sync warnings in the client settings UI without hanging in a loading state, and reject concurrent sync invocations when a sync is already running.

## Impact

- **Affected code**: `client-tauri/src-tauri/src/sync.rs`, `client-tauri/src/Settings.tsx`, `client-tauri/src-tauri/src/lib.rs`
- **APIs**: No API changes.
- **Dependencies**: No new dependencies.
- **Behavior**: Failed/skipped transfers will not be falsely recorded as synchronized; the settings UI will cleanly reset and display warnings when transfers are skipped; manual sync will no longer run concurrently with active background sync cycles.
