## Context

See `proposal.md` for motivation.

In `client-tauri/src-tauri/src/lib.rs`:
- Manual sync triggered from GUI (`run_sync`) records `sync_ok` and `last_sync_at` and dispatches `client.client_ping(Some(sync_ok), Some(last_sync_at))`.
- Periodic background sync (`spawn_background_sync_loop`) runs the same `sync::run_sync(&mut client, &root)` and updates local UI state, but omitted the call to `client.client_ping`.

In `backend/tests/test_telemetry.py`:
- `test_telemetry_api_routes` seeded a summary with `"started_at": "2026-09-16T21:00:00Z"`.
- `app.telemetry.service.ingest_telemetry_batch` invokes `prune_telemetry_records`, which deletes any summary older than `now - timedelta(days=30)`.
- When tests execute >30 days past September 16, 2026, the newly ingested summary is immediately deleted during ingestion, causing assertions to fail.

## Goals / Non-Goals

**Goals:**
- Unify sync outcome reporting across manual and background synchronization loops in `client-tauri`.
- Make telemetry test timestamps dynamic and resilient to arbitrary future test run dates.
- Keep all fixes strictly scoped, non-breaking, and with zero changes to existing public API schemas.

**Non-Goals:**
- Changing the retention window duration (30 days remains the server default).
- Adding retry queues for `client_ping` (pings remain best-effort, subsequent sync cycles naturally update server state).

## Decisions

### 1. Replicate `client_ping` invocation pattern in `spawn_background_sync_loop`
- **Choice**: Right after `sync::run_sync(&mut client, &root)` completes in `spawn_background_sync_loop`, capture:
  ```rust
  let sync_ok = result.is_ok();
  let last_sync_at = chrono::Utc::now().to_rfc3339();
  ```
  and invoke:
  ```rust
  if let Err(e) = client.client_ping(Some(sync_ok), Some(last_sync_at)) {
      log::warn!("client_ping failed: {}", e);
  }
  ```
- **Rationale**: Matches the behavior of `run_sync` exactly. Any failure to ping is logged at `WARN` level and does not terminate the background loop.

### 2. Dynamic UTC timestamps in test fixture
- **Choice**: Use Python's `datetime.now(timezone.utc)` to compute `started_at` (5 minutes ago) and `completed_at` (4 minutes ago) formatted as ISO 8601 strings (`.strftime("%Y-%m-%dT%H:%M:%SZ")`).
- **Rationale**: Matches the pattern already established in `test_sync_summary_and_diagnostic_event_crud_and_pruning`, ensuring fixtures never expire regardless of calendar year.

## Risks / Trade-offs

- **[Risk]** Network error during client ping in background thread.
  - *Mitigation*: Handled as non-fatal with `log::warn!`, identical to manual sync. Next background interval (60s) will attempt sync and ping again.
