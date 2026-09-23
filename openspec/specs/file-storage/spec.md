## Purpose

Provides secure filesystem storage, path isolation, and directory listings for Brandy Box users.

## Requirements

### Requirement: Email Path Sanitization Allows Plus Aliasing
The storage layer SHALL allow valid email addresses containing plus characters (e.g., `user+alias@domain.com`) to be used as root user storage directory names without throwing validation errors.

#### Scenario: User with plus in email accesses file list
- **WHEN** an authenticated user with an email containing `+` requests `GET /api/files/list`
- **THEN** the system resolves their user directory successfully and returns HTTP 200 with the file list instead of HTTP 500

#### Scenario: User with plus in email uploads a file
- **WHEN** an authenticated user with an email containing `+` uploads a file via `POST /api/files/upload`
- **THEN** the system resolves their user path and accepts the upload without raising an invalid email error

### Requirement: Internal Upload Directory Isolation
The file and folder listing endpoints SHALL exclude internal scratch directories, specifically `.uploads` and its contents, from user-visible file and directory responses.

#### Scenario: Listing files while chunked upload is in progress
- **WHEN** a client initiates a chunked upload creating `.uploads/<upload_id>/` and requests `GET /api/files/list`
- **THEN** the system response excludes all files under `.uploads`

#### Scenario: Listing folders while chunked upload is in progress
- **WHEN** a client has an active or abandoned chunked upload directory and requests `GET /api/files/folders`
- **THEN** the system response excludes `.uploads` and all subdirectories beneath it

#### Scenario: Direct access to internal upload directory
- **WHEN** a client attempts to download or delete a file path starting with `.uploads`
- **THEN** the system rejects the request with a bad request or access denied error
