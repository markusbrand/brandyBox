## Purpose

Provides centralized, correlated diagnostic telemetry, structured error reporting, sync run summaries, and request tracing between syncing clients and the backend service.

## ADDED Requirements

### Requirement: Correlation identifier generation and propagation
The client and server SHALL associate every synchronization run with a unique correlation identifier to link client actions to server requests.

#### Scenario: Client initiates a sync cycle with trace header
- **WHEN** the client starts a sync cycle
- **THEN** it generates a unique `trace_id` (prefixed with `sync-`) and passes it in the `X-Sync-ID` HTTP header for all API requests within that cycle.

#### Scenario: Backend middleware captures trace header
- **WHEN** the backend receives an HTTP request containing an `X-Sync-ID` header
- **THEN** it binds the identifier to request context and includes it in all server log messages and diagnostic records emitted during request processing.

### Requirement: Structured error capture and classification
The client SHALL capture structured error events including error codes, operation phases, and relevant context whenever an error occurs during synchronization.

#### Scenario: File transfer encounters a timeout or failure
- **WHEN** a file upload, chunk upload, or download fails due to network error, HTTP status, or disk I/O
- **THEN** the client records a diagnostic event containing timestamp, trace_id, level, category, error_code, error message, and context details (file path, chunk index, byte count, HTTP status).

### Requirement: Sync cycle summary reporting
The client SHALL compile and submit a comprehensive summary upon concluding each synchronization run.

#### Scenario: Sync cycle finishes
- **WHEN** a synchronization cycle completes (whether successful, with warnings, or failed)
- **THEN** the client compiles a summary record including duration, files scanned, files uploaded, files downloaded, failure count, and status, and submits it to the backend.

### Requirement: Central diagnostic event ingestion API
The backend SHALL expose an authenticated endpoint allowing clients to submit batches of diagnostic events and sync summaries.

#### Scenario: Client submits diagnostic batch
- **WHEN** a client POSTs an event batch to `/api/telemetry/events` with valid user authentication
- **THEN** the backend validates the payload, persists events and summaries into SQLite tables (`diagnostic_events` and `sync_summaries`), and returns HTTP 202 Accepted or 204 No Content.

### Requirement: Offline telemetry buffering
The client SHALL buffer diagnostic events locally when the backend is unreachable and flush them upon reconnection.

#### Scenario: Sync fails while network or backend is unreachable
- **WHEN** an error occurs and the backend cannot be contacted to ingest the event
- **THEN** the client stores the event in a persistent local queue and flushes pending events upon the next successful connection.
