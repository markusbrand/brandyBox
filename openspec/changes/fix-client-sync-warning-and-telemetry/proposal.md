## Why

During codebase investigation and manual sync error simulations, three concrete, tightly coupled bugs were identified in the native desktop client sync lifecycle:
1. **Permanent UI Hang on Warning Status**: In `client-tauri/src/Settings.tsx`, the `sync-status` event listener only checks `if (status === "synced" || status === "error")`. When `sync::run_sync` finishes with non-fatal issues (e.g. invalid filenames, path traversal attempts, or partial upload skips) and emits `SyncStatus::Warning(msg)`, `setSyncing(false)` is never called. The UI permanently hangs with "Syncing..." active, the "Sync now" button remains permanently disabled, progress polling continues indefinitely, and the user is never shown the warning message.
2. **Missing Telemetry in Background Sync Loop**: In `client-tauri/src-tauri/src/lib.rs`, `spawn_background_sync_loop` executes periodic sync runs but never invokes `client.client_ping(Some(sync_ok), Some(last_sync_at))`, unlike the manual `run_sync` command. Consequently, automated background sync activity is never reported to `POST /api/clients/ping`, leaving operator diagnostics on the backend (`/api/admin/clients`) completely unaware of client health unless the user manually opens Settings and clicks "Sync now".
3. **Missing Mutual Exclusion for Sync Operations**: Neither the `run_sync` Tauri command nor the underlying `sync::run_sync` function enforce single-instance mutual exclusion. If a user triggers "Sync now" while a background sync is actively downloading/uploading, or if a slow network causes overlapping executions, both sync threads run concurrently against the same local folder. This causes race conditions on temporary files (`.{name}.tmp_download`), file rename collisions, and clobbered `sync_state.json` metadata.

## What Changes

- **Desktop Client Frontend (`Settings.tsx`)**:
  - Update `sync-status` listener to handle `status === "warning"`: reset `syncing` to `false`, clear sync progress, reload settings, and store the warning message in state.
  - Track `syncStatus` (`idle`, `syncing`, `synced`, `warning`, `error`) so the MUI `Alert` renders with appropriate severity (`warning` vs `error`).
  - In initial mount `get_sync_status` effect, accurately reflect `warning` (display alert) and `syncing` (set `syncing(true)`).
- **Desktop Client Background Sync Telemetry (`lib.rs`)**:
  - In `spawn_background_sync_loop`, call `client.client_ping(Some(sync_ok), Some(last_sync_at))` after each sync attempt (or error), matching the manual sync behavior and reporting client version and sync status to the backend.
- **Sync Mutual Exclusion (`sync.rs` & `lib.rs`)**:
  - Enforce atomic single-instance execution in `sync::run_sync` using an atomic synchronization guard (e.g. `AtomicBool`), immediately returning an error/warning if another sync is already in progress.
  - In `run_sync` Tauri command, check current sync status and reject invocation if a sync is already active.

## Capabilities

### Modified Capabilities
- `desktop-client`: Adds requirements for UI handling of sync warning states, background sync telemetry reporting via client ping, and sync concurrency protection.

## Impact

- **Client Rust Backend**: `client-tauri/src-tauri/src/lib.rs`, `client-tauri/src-tauri/src/sync.rs`.
- **Client Frontend**: `client-tauri/src/Settings.tsx`.
- **API/Backend Compatibility**: Fully backward compatible; uses existing `POST /api/clients/ping` endpoint.
- **Dependencies**: No new external dependencies required.
