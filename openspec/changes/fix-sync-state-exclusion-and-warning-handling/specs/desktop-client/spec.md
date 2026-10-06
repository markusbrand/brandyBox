## ADDED Requirements

### Requirement: Exclusion of Incomplete or Skipped Transfers from Synced State
The desktop client synchronization engine SHALL exclude files with pending, failed, or skipped downloads or uploads from the persistent synchronized paths list (`sync_state.json`), ensuring only verified and successfully synchronized files are recorded as in-sync.

#### Scenario: Skipped or failed download of an existing file
- **WHEN** an existing file has a newer version on the remote server and is scheduled for download, but the download fails or is skipped during synchronization
- **THEN** the file is omitted from the saved synchronized paths list (`state.paths`), preventing false in-sync state and protecting against premature local file deletions on subsequent cycles

#### Scenario: Skipped or failed upload of an existing file
- **WHEN** an existing file has local changes and is scheduled for upload, but the upload fails or is skipped during synchronization
- **THEN** the file is omitted from the saved synchronized paths list (`state.paths`), preventing false in-sync state

### Requirement: Desktop Client Sync Warning Notification and State Recovery
The desktop client user interface SHALL handle `warning` synchronization status events by terminating the active syncing state, resetting progress indicators, refreshing account storage data, and displaying the warning message to the user.

#### Scenario: Sync completes with skipped files warning
- **WHEN** a synchronization cycle finishes with skipped downloads or uploads and emits a `warning` status event
- **THEN** the settings user interface resets the `syncing` indicator to false, clears the progress bar, re-enables the "Sync now" button, reloads storage stats, and displays a visible warning alert containing the warning message

### Requirement: Concurrency Guard for Manual Sync Invocations
The desktop client SHALL reject or ignore manual synchronization requests triggered via the user interface or system tray while another synchronization cycle is already actively executing.

#### Scenario: Manual sync invoked while sync is already active
- **WHEN** a manual sync is requested via the UI or tray while `status == "syncing"`
- **THEN** the client does not spawn a concurrent worker thread and returns without interfering with the in-progress sync cycle
