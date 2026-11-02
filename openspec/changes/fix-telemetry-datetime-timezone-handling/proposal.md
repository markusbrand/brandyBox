## Why

Telemetry logging and pruning in `backend/app/telemetry/service.py` crashes with `TypeError: can't compare offset-naive and offset-aware datetimes` whenever `log_server_event` is called or when naive datetimes are ingested. Furthermore, `brandybox-doctor` timeline sorting crashes when ordering mixed naive and aware timestamps, and `test_telemetry.py::test_telemetry_api_routes` failed due to hardcoded timestamps falling outside the 30-day retention pruning window. Resolving timezone normalization and bulk deletion session synchronization prevents server crashes on logging events, ensures telemetry pruning functions reliably, and eliminates time-bomb test failures.

## What Changes

- Explicitly pass `created_at=datetime.now(timezone.utc)` when creating `ServerEvent` records in `backend/app/telemetry/service.py:log_server_event`.
- Execute bulk retention deletions in `prune_telemetry_records` with `synchronize_session=False` to prevent SQLAlchemy ORM in-memory evaluation mismatches across timezone formats.
- Normalize client timestamps in `ingest_telemetry_batch` to UTC aware datetimes if naive timestamps are supplied.
- Normalize timeline timestamps to UTC before sorting in `backend/app/cli/doctor.py` (`show_trace` and `generate_llm_prompt`).
- Update `backend/tests/test_telemetry.py` to use dynamic, relative UTC timestamps for test telemetry batches and add regression tests for `log_server_event` pruning and naive datetime ingestion.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `central-telemetry`: Require the backend telemetry service and ingestion pipeline to normalize timestamps to UTC and safely prune retention records without offset-naive comparison crashes.
- `pi-diagnostics-cli`: Require `brandybox-doctor` to safely sort trace and prompt timelines regardless of whether constituent timestamps are naive or timezone-aware.

## Impact

- **Affected code**: `backend/app/telemetry/service.py`, `backend/app/cli/doctor.py`, `backend/tests/test_telemetry.py`
- **APIs**: No breaking API schema changes; `/api/telemetry/events` accepts both naive and aware ISO timestamps cleanly.
- **Dependencies**: No new dependencies.
- **Behavior**: Eliminates runtime `TypeError` crashes during server event logging, batch ingestion, and doctor CLI timeline generation.
