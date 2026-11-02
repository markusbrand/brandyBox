## ADDED Requirements

### Requirement: Client connection ping and sync state retention
The backend SHALL maintain the latest client connection details per user and client type, updating client version and last seen timestamp while preserving existing sync status when incoming pings omit sync outcome fields.

#### Scenario: Client reports sync outcome
- **WHEN** a client submits a ping request to `/api/clients/ping` with `last_sync_at` and `last_sync_ok`
- **THEN** the backend updates the client connection record with the provided sync timestamp and success status.

#### Scenario: Client sends heartbeat ping omitting sync outcome
- **WHEN** a client submits a ping request to `/api/clients/ping` with null or omitted `last_sync_at` and `last_sync_ok` after a previous ping recorded sync status
- **THEN** the backend updates `last_seen_at`, `client_version`, and `backend_version_at_ping` while retaining the existing `last_sync_at` and `last_sync_ok` values.
