## ADDED Requirements

### Requirement: Exclusion of Remotely Deleted Files from Upload Candidates
The desktop client synchronization engine SHALL exclude files that are identified for local deletion (files removed from the remote server since the last sync) from the upload candidate list, ensuring deleted files are not scheduled for upload.

#### Scenario: Clean synchronization after remote file deletion
- **WHEN** a previously synchronized file is removed on the remote server
- **THEN** the file is deleted locally and is excluded from upload candidates, completing the sync cycle with `SyncStatus::Synced` without raising skipped-upload warnings or incrementing failure telemetry counts
