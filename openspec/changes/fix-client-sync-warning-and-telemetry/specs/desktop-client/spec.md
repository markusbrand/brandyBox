## ADDED Requirements

### Requirement: Sync Warning State and Progress Recovery
The desktop client settings UI SHALL handle warning sync status events, clear the active syncing state, terminate polling, and display the warning message to the user.

#### Scenario: Sync completes with warnings
- **WHEN** a synchronization run finishes with non-fatal issues and emits a `warning` status with a descriptive message
- **THEN** the UI resets the syncing state to false, stops the progress polling interval, reloads current settings, and displays the warning message in an alert

#### Scenario: Settings window opened while client has a warning status
- **WHEN** the settings view initializes and queries the current client status
- **THEN** if the status is `warning`, the client displays the warning alert rather than remaining silent or frozen

### Requirement: Background Synchronization Telemetry Reporting
The desktop client background sync loop SHALL report synchronization results and timestamps to the central server via the client ping endpoint after every sync execution.

#### Scenario: Background sync completes successfully
- **WHEN** the periodic background sync task runs to completion without errors
- **THEN** the client sends a ping request to `/api/clients/ping` containing `sync_ok = true` and the current ISO timestamp

#### Scenario: Background sync fails with an error
- **WHEN** the periodic background sync task encounters an error or network failure
- **THEN** the client sends a ping request to `/api/clients/ping` containing `sync_ok = false` and the current ISO timestamp

### Requirement: Sync Concurrency and Mutual Exclusion
The desktop client SHALL enforce mutual exclusion on synchronization runs, preventing concurrent sync processes from executing simultaneously on the same local directory.

#### Scenario: User triggers manual sync while a sync is already running
- **WHEN** the user invokes the manual sync action while a background or manual sync is actively executing
- **THEN** the request is rejected with a message indicating that synchronization is already in progress, without launching a concurrent sync thread

#### Scenario: Background sync timer fires while a sync is already running
- **WHEN** the background sync timer interval elapses while an active sync operation is executing
- **THEN** the new sync execution attempt is skipped or deferred until the active sync has finished
