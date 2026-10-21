## Context

See proposal.md for motivation and problem background.

Currently, `run_sync` in `client-tauri/src-tauri/src/lib.rs` executes `client.client_ping(Some(sync_ok), Some(last_sync_at))` after running sync, but `spawn_background_sync_loop` in the same file omits this call entirely. Additionally, `Settings.tsx` only handles terminal states (`"synced"`, `"error"`, `"warning"`) in its `sync-status` listener and initial mount fetch, ignoring `"syncing"` events.

## Goals / Non-Goals

**Goals:**
- Ensure the background sync loop reports client version and outcome via `client.client_ping(...)` matching `run_sync`.
- Ensure `Settings.tsx` transitions to `syncing: true` whenever `"syncing"` status is received or queried, clearing previous error/warning banners and engaging progress polling.

**Non-Goals:**
- Modify backend telemetry models or ping endpoints.
- Alter sync concurrency locking or interval scheduling.

## Decisions

### 1. Call `client_ping` with best-effort error handling in `spawn_background_sync_loop`
- **Choice**: Call `if let Err(e) = client.client_ping(Some(sync_ok), Some(last_sync_at)) { log::warn!("client_ping failed: {}", e); }` before emitting the final `sync-status` payload.
- **Rationale**: Matches the implementation in `run_sync` exactly and prevents any ping failure from affecting local sync state or disrupting the background sync thread.
- **Alternatives considered**: Spawning a separate detached thread for `client_ping`. Unnecessary because `client_ping` is a fast HTTP call with standard timeout, and `spawn_background_sync_loop` already runs in its own background worker thread.

### 2. Handle `"syncing"` status in `Settings.tsx`
- **Choice**: In `Settings.tsx`, check `if (status === "syncing") { setSyncing(true); setSyncError(null); setSyncWarning(null); }` in both the `sync-status` event listener and the initial `get_sync_status` call.
- **Rationale**: Keeps the UI responsive to background sync starts and ensures that opening the Settings window while sync is running accurately reflects the ongoing operation.

## Risks / Trade-offs

- [Telemetry Ping Failure] → Network errors during ping are caught and logged at `log::warn` without failing sync or breaking the daemon loop.
- [UI State Thrashing] → State updates only fire when events are received or on initial window mount, matching existing event handling patterns.
