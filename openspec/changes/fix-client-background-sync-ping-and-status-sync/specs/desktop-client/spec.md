## ADDED Requirements

### Requirement: Background Sync Telemetry Reporting
The desktop client SHALL report client version and synchronization status via the client ping endpoint after completing each background synchronization cycle.

#### Scenario: Background sync completes successfully
- **WHEN** the background synchronization loop completes a sync pass without errors
- **THEN** the client sends a telemetry ping to `/api/clients/ping` with `last_sync_ok: true` and the ISO timestamp of the sync completion

#### Scenario: Background sync encounters an error
- **WHEN** the background synchronization loop encounters an error during a sync pass
- **THEN** the client sends a telemetry ping to `/api/clients/ping` with `last_sync_ok: false` and the ISO timestamp before or alongside updating local error status

### Requirement: User Interface Active Synchronization State
The desktop client settings user interface SHALL synchronize its active state with background synchronization events and current execution status.

#### Scenario: Background synchronization begins
- **WHEN** the synchronization engine emits a `sync-status` event with `{"status": "syncing"}`
- **THEN** the settings user interface transitions to the syncing state, disables redundant manual sync triggers, and begins polling progress

#### Scenario: Settings window opened during active synchronization
- **WHEN** the user opens the settings window while synchronization is in progress
- **THEN** the settings window detects the active status and transitions immediately to the syncing state with progress polling active
