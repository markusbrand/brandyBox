## ADDED Requirements

### Requirement: Retention of Hash-Verified and Resumed Downloads in Synced State
The desktop client synchronization engine SHALL retain files whose content is verified identical to the remote server or whose download was completed in a previous cycle in the persistent synchronized paths list (`sync_state.json`), ensuring they are recorded as synchronized and preventing false download resurrection on subsequent cycles.

#### Scenario: Download skipped due to matching content hash
- **WHEN** a file scheduled in `to_download` has an existing local file whose computed hash matches the remote server hash
- **THEN** the download payload transfer is skipped, the file hash is recorded in `state.file_hashes`, and the file path is added to `completed_downloads` so that it is preserved in `state.paths` (`sync_state.json`)

#### Scenario: Download skipped due to previous download completion
- **WHEN** a file scheduled in `to_download` was already downloaded in an interrupted sync cycle and exists on disk
- **THEN** the download is skipped and the file path is added to `completed_downloads` so that it is preserved in `state.paths` (`sync_state.json`)

### Requirement: Exclusion of Git Repository Metadata and Worktree Files
The desktop client synchronization engine SHALL ignore `.git` directory trees, bare `.git` files, and worktree or submodule pointer files across all directory levels.

#### Scenario: Bare .git file at sync folder root or subdirectories
- **WHEN** a file named `.git` exists in the sync root or in any subdirectory
- **THEN** `is_ignored` returns true, excluding the file from local file scans, uploads, and downloads
