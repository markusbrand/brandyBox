## Why

Clients send periodic heartbeats or presence pings (such as on web login or during background loops) where sync status (`last_sync_at` and `last_sync_ok`) is omitted. The backend `upsert_client_ping` function currently performs an unconditional SQLite `ON CONFLICT DO UPDATE` that sets `last_sync_at` and `last_sync_ok` directly to excluded values, overwriting previously recorded sync timestamps and success flags with `NULL`. This erases client sync status history and causes admin telemetry queries to report missing sync state.

## What Changes

- Modify `upsert_client_ping` in `app/telemetry/service.py` to use `func.coalesce` so that incoming NULL sync fields (`last_sync_at`, `last_sync_ok`) preserve the existing values in `client_connections`.
- Add test coverage verifying that subsequent pings with null sync statuses do not erase earlier recorded sync outcomes.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `central-telemetry`: Update client ping ingestion behavior so that heartbeats and pings omitting sync status retain prior sync status records rather than resetting them to null.

## Impact

- Affected Code: `backend/app/telemetry/service.py` (`upsert_client_ping`) and `backend/tests/test_web_features.py` / `backend/tests/test_telemetry.py`.
- No database migrations or API contract breaking changes; purely preserves existing row data on conflict update.
