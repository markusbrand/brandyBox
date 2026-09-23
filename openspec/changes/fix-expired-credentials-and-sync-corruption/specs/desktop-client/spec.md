## ADDED Requirements

### Requirement: Expired Credential Filtering and Purging
The desktop client SHALL filter out expired JWT refresh tokens and purge invalid credentials when authentication refresh fails with HTTP 401 Unauthorized.

#### Scenario: Expired refresh token in storage
- **WHEN** stored credentials contain a JWT whose expiration timestamp is in the past
- **THEN** `get_stored()` returns `None` instead of returning the expired credentials

#### Scenario: Server rejects refresh token with 401 Unauthorized
- **WHEN** an access token refresh attempt receives HTTP 401 Unauthorized from the server
- **THEN** the client purges stored credentials via `clear_stored()` to halt further refresh loops

### Requirement: Sync Path Confinement to Local Root
The sync engine SHALL sanitize all file paths and verify that local paths remain strictly confined within the configured sync folder root.

#### Scenario: Path with leading slashes
- **WHEN** a remote file path has leading slashes (e.g., `/notes.txt`)
- **THEN** the sync engine normalizes the path to `notes.txt` and joins it safely within `local_root`

#### Scenario: Path with directory traversal components
- **WHEN** a file path contains `..` or resolves outside `local_root`
- **THEN** the sync engine rejects the file operation and records a warning without touching files outside `local_root`
