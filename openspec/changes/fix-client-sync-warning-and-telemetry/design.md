## Context

See `proposal.md` for motivation.

The desktop client synchronizes files between the local filesystem and the BrandyBox server. Synchronization is initiated either manually by the user from the Settings window (`run_sync` Tauri command) or automatically on an interval by a background task spawned in `spawn_background_sync_loop`.

When synchronization runs, `sync::run_sync` emits status updates via Tauri event `sync-status` with a `SyncStatus` variant (`Starting`, `Syncing`, `Synced`, `Warning`, `Error`). However, the UI event listener and mount hooks only check for `synced` and `error`, ignoring `warning` events and leaving UI state in a permanent syncing loop. Additionally, `spawn_background_sync_loop` fails to report synchronization telemetry to the server, and no mutual exclusion lock prevents concurrent sync executions.

## Goals / Non-Goals

**Goals:**
- Provide complete UI lifecycle recovery in `Settings.tsx` when a sync finishes with warnings, rendering appropriate alert severity (`warning`).
- Ensure background sync executions notify the central backend via `client.client_ping(Some(sync_ok), Some(last_sync_at))` to keep operator telemetry updated.
- Guarantee strict mutual exclusion so that at most one sync process runs at any time, protecting local state files and temporary download files.
- Add unit tests verifying the mutual exclusion guard in `sync.rs`.

**Non-Goals:**
- Modifying backend ping endpoint contracts or database schemas (existing endpoints accept `sync_ok` and `last_sync_at`).
- Redesigning the entire sync engine protocol or conflict resolution strategy.

## Decisions

### 1. UI State Machine and Alert Severity in `Settings.tsx`
- **Decision**: Introduce explicit `syncStatus` state in `Settings.tsx` (`"idle" | "syncing" | "synced" | "warning" | "error"`).
- **Rationale**: When `sync-status` receives `status === "warning"`, `setSyncing(false)`, clear progress, reload settings, and store the warning message. The MUI `Alert` component will use `severity={syncStatus === "warning" ? "warning" : "error"}` to clearly distinguish non-fatal warnings (e.g. skipped files, path normalization warnings) from fatal failures.
- **Alternatives Considered**: Treating warning as an error. Rejected because warnings represent partial completion (some files synced, non-fatal skips), whereas error represents full failure.

### 2. Telemetry Ping in `spawn_background_sync_loop`
- **Decision**: Call `client.client_ping(Some(sync_ok), Some(last_sync_at))` after each sync cycle in `spawn_background_sync_loop`.
- **Rationale**: Mirrors the exact behavior of manual `run_sync` in `lib.rs` (lines 330–333). Silently ignoring background sync pings causes `client_connections.last_sync_at` to remain stale on the central server.
- **Alternatives Considered**: Emitting an event to the frontend to perform the ping. Rejected because the frontend window may be closed while background sync runs.

### 3. RAII Atomic Mutual Exclusion Lock in `sync.rs`
- **Decision**: Protect `sync::run_sync` with an atomic guard `SYNC_IN_PROGRESS: AtomicBool` using `compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst)`.
- **Rationale**: An RAII drop guard guarantees the flag is reset to `false` even if `run_sync` returns early or encounters an error. Fast atomic check prevents race conditions between manual button clicks and scheduled background ticks.
- **Alternatives Considered**: Using a Tokio mutex. Rejected because `run_sync` executes synchronous blocking I/O across std threads; `AtomicBool` with an RAII guard is simpler, lockless, and immune to deadlocks.

## Risks / Trade-offs

- **[Risk] Background sync skipping when manual sync is in progress** → Mitigation: If a background interval fires while a manual sync is running, it logs an info message and gracefully skips the interval. The next interval will sync any pending changes.
- **[Risk] Window closed during manual sync** → Mitigation: Tauri commands execute on background threads and the lock is tied to the sync thread lifetime, not the frontend window lifecycle.
