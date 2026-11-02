## MODIFIED Requirements

### Requirement: Central diagnostic event ingestion API
The backend SHALL expose an authenticated endpoint allowing clients to submit batches of diagnostic events and sync summaries, normalizing client timestamps to timezone-aware UTC and safely executing retention pruning.

#### Scenario: Client submits diagnostic batch
- **WHEN** a client POSTs an event batch to `/api/telemetry/events` with valid user authentication
- **THEN** the backend validates the payload, persists events and summaries into SQLite tables (`diagnostic_events` and `sync_summaries`), normalizes any offset-naive timestamps to UTC, executes retention pruning without comparison crashes, and returns HTTP 202 Accepted or 204 No Content.

#### Scenario: Client submits events with naive timestamps
- **WHEN** a client submits events or sync summaries with offset-naive ISO timestamps
- **THEN** the backend coerces timestamps to UTC timezone-aware values without raising comparison errors during retention pruning or persistence.
