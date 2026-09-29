## ADDED Requirements

### Requirement: Clock-Skew Resilient Modification Detection and Synchronization
The desktop sync engine SHALL detect and synchronize file modifications using 3-way content hash comparisons against the recorded sync base, ensuring local edits are uploaded even when the local file modification timestamp is older than or equal to the remote timestamp (such as under clock skew or archive extraction).

#### Scenario: Local file edited with clock lagging behind server
- **WHEN** a file previously synchronized has an unchanged server hash matching the recorded base hash, but the local file hash differs and the local timestamp is less than or equal to the server timestamp
- **THEN** the sync engine schedules the file for upload rather than download, preserving user modifications without stalling or overwriting

#### Scenario: Remote file edited with clock lagging behind client
- **WHEN** a file previously synchronized has an unchanged local file hash matching the recorded base hash, but the remote hash differs and the remote timestamp is less than or equal to the local timestamp
- **THEN** the sync engine schedules the file for download rather than upload

#### Scenario: Download execution disk hash verification
- **WHEN** a file is scheduled for download because local contents differ from remote contents
- **THEN** the download execution loop does not skip downloading based on stale cached state if the actual file on disk differs from the remote hash

### Requirement: Upload and Deletion Hash State Cache Consistency
The desktop sync engine SHALL maintain consistency of its cached file hashes across upload and deletion operations.

#### Scenario: Hash cache update upon successful upload
- **WHEN** a local file is successfully uploaded to the server
- **THEN** the sync engine computes and inserts the file's SHA-256 hash into the persisted file hash state cache

#### Scenario: Hash cache pruning upon file deletion
- **WHEN** a file is deleted from the server or local disk
- **THEN** the sync engine removes the file's hash entry from the persisted file hash state cache

### Requirement: Non-Resurrection of Failed Local Deletions
The desktop sync engine SHALL preserve failed local deletions in its synchronized state and raise a warning rather than resurrecting the file on subsequent sync cycles.

#### Scenario: Local deletion fails due to lock or permission error
- **WHEN** a file deleted on the server fails to be deleted on the local filesystem
- **THEN** the sync engine logs a diagnostic event, retains the file path in `state.paths`, and emits a sync warning so that subsequent sync cycles retry local deletion instead of uploading the file as a new local creation
