## MODIFIED Requirements

### Requirement: Internal System Directory Isolation
The file and folder listing endpoints and path resolution SHALL exclude internal system directories (specifically `.uploads` and `.brandybox`) from user-visible file and directory responses, and SHALL reject direct access attempts to these directories.

#### Scenario: Listing files when internal directories exist
- **WHEN** an authenticated user has files under `.brandybox` or `.uploads` and requests `GET /api/files/list`
- **THEN** the system response excludes all files under `.brandybox` and `.uploads`

#### Scenario: Listing folders when internal directories exist
- **WHEN** an authenticated user has internal directories `.brandybox` or `.uploads` and requests `GET /api/files/folders`
- **THEN** the system response excludes `.brandybox` and `.uploads` and all subdirectories beneath them

#### Scenario: Direct access to internal directories
- **WHEN** a client attempts to download, upload, or delete a file path targeting `.brandybox` or `.uploads`
- **THEN** the system rejects the request with HTTP 400 Bad Request
