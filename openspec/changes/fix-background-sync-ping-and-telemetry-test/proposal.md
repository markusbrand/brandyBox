## Why

Two concrete bugs currently affect BrandyBox's telemetry and monitoring subsystems:
1. In `client-tauri`, `spawn_background_sync_loop` executes periodic background synchronization runs but completely omits the `client.client_ping(Some(sync_ok), Some(last_sync_at))` call that is performed during manual sync (`run_sync`). Consequently, central server monitoring (`GET /api/admin/clients` and `brandybox-doctor --summary`) displays active clients as disconnected or never synchronized unless manual synchronization is triggered in the GUI.
2. In `backend/tests/test_telemetry.py`, `test_telemetry_api_routes` inserts a hardcoded static timestamp (`2026-09-16T21:00:00Z`). Because `ingest_telemetry_batch` enforces a 30-day retention cleanup via `prune_telemetry_records`, any test run more than 30 days after September 16, 2026 immediately deletes the newly ingested summary, causing the test suite assertion `assert any(s["trace_id"] == "sync-api-test-01" for s in summaries)` to fail.

Fixing these ensures accurate client observability in the central monitoring dashboard and stabilizes the backend automated test suite.

## What Changes

- **Desktop Client Background Ping Telemetry**: Update `spawn_background_sync_loop` in `client-tauri/src-tauri/src/lib.rs` to compute `sync_ok` and `last_sync_at`, invoking `client.client_ping(Some(sync_ok), Some(last_sync_at))` upon completion of each background sync run.
- **Dynamic Telemetry Test Timestamps**: In `backend/tests/test_telemetry.py`, replace static September 2026 timestamp strings with dynamic UTC timestamps relative to `datetime.now(timezone.utc)` so ingested records remain within the 30-day retention window during test assertions.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `central-telemetry`: Clarify requirement that client ping telemetry (`POST /api/clients/ping`) SHALL be dispatched upon completion of both manual and automatic background synchronization cycles.

## Impact

- `client-tauri/src-tauri/src/lib.rs`: Background sync loop dispatches `client_ping`.
- `backend/tests/test_telemetry.py`: Test fixtures generate valid dynamic timestamps.
- Admin dashboard (`/api/admin/clients`) and CLI (`brandybox-doctor --summary`): Accurately reflect active client synchronization activity from background daemons.
