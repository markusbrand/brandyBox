## ADDED Requirements

### Requirement: Canonical Relative Path Normalization and Hash Synchronization
The file storage endpoints SHALL normalize all user-supplied file path parameters into canonical relative paths (forward slashes, no leading or trailing slashes, no duplicate slashes) across uploads, listings, and deletions, ensuring that stored content hashes in `file_hashes` correspond directly to the paths returned by file listings and that hashes are cleanly purged on deletion.

#### Scenario: File uploaded with leading slash has content hash in file listing
- **WHEN** an authenticated user uploads a file with a leading slash in the path parameter (e.g. `path=/docs/notes.txt`)
- **THEN** the system resolves and stores the file, records its content hash under the canonical relative path (`docs/notes.txt`), and subsequent `GET /api/files/list` requests include the computed SHA-256 hash for that file

#### Scenario: File uploaded with Windows backslashes is normalized
- **WHEN** an authenticated user uploads a file with backslashes in the path parameter (e.g. `path=docs\notes.txt`)
- **THEN** the system normalizes the path to forward slashes (`docs/notes.txt`), stores its hash under the canonical relative path, and returns the canonical path in the response

#### Scenario: Deleting a file removes its associated hash record
- **WHEN** an authenticated user deletes an existing file via `DELETE /api/files/delete`
- **THEN** the system removes the file from the filesystem and removes the corresponding hash record from the database, preventing orphaned hash entries

#### Scenario: Overwriting a file with smaller content clamps storage usage to non-negative
- **WHEN** an authenticated user uploads a file replacing a larger existing file when cached user storage usage is low
- **THEN** the system updates `current_user.storage_used_bytes` without allowing it to underflow below 0
