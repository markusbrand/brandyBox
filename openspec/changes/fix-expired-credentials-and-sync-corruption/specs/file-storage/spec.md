## ADDED Requirements

### Requirement: Upload Directory Collision Prevention
The file storage endpoints SHALL reject upload requests targeting an existing directory path with HTTP 409 Conflict.

#### Scenario: Direct file upload targeting existing directory
- **WHEN** a client uploads a file via `POST /api/files/upload` where the destination path is an existing directory
- **THEN** the server returns HTTP 409 Conflict and preserves the existing directory without moving files into it

#### Scenario: Chunked upload initialization targeting existing directory
- **WHEN** a client initiates a chunked upload via `POST /api/files/upload/init` where the destination path is an existing directory
- **THEN** the server returns HTTP 409 Conflict without creating upload scratch directories

#### Scenario: Chunked upload finalize targeting existing directory
- **WHEN** a chunked upload is finalized via `POST /api/files/upload/finalize` and the target path is an existing directory
- **THEN** the server returns HTTP 409 Conflict and cleans up temporary assembly files

### Requirement: Chunked Upload Contiguity Verification
The chunked upload assembly service SHALL verify that all chunks from index 0 through N-1 are present before assembling the destination file.

#### Scenario: Finalizing an upload with missing chunks
- **WHEN** `POST /api/files/upload/finalize` is invoked and any intermediate chunk index is missing
- **THEN** the server rejects the request with HTTP 400 Bad Request and does not assemble an incomplete file
