## Purpose

Manages the native desktop client lifecycle, application termination controls, autostart integration, and robust file download synchronization.

## Requirements

### Requirement: Explicit Application Quit Support
The desktop client SHALL allow the application to exit when explicit quit commands are triggered, while preventing exit when the main window is merely closed.

#### Scenario: User quits via menu bar or keyboard shortcut
- **WHEN** the user triggers "Quit Brandy Box" from the application menu or presses `Cmd+Q` on macOS
- **THEN** the application terminates normally rather than intercepting and preventing the exit

#### Scenario: User closes the settings window
- **WHEN** the user closes the main settings window
- **THEN** the window is hidden and the background synchronization process continues running

### Requirement: Absolute Path in Autostart Configuration
The desktop client SHALL configure system autostart using an absolute path to the executable binary.

#### Scenario: macOS login LaunchAgent execution
- **WHEN** autostart is enabled on macOS
- **THEN** the generated `rocks.brandstaetter.brandybox.plist` contains the absolute path to the executable in `ProgramArguments`, allowing `launchd` to invoke it successfully at login

### Requirement: Resilient Temporary Download Files
The desktop client SHALL download files to a non-colliding temporary filename and ensure incomplete download files are excluded from synchronization upload scans.

#### Scenario: Download of file ending in tmp_download
- **WHEN** a file named `*.tmp_download` is downloaded
- **THEN** the destination file is not truncated prior to successful download completion

#### Scenario: Files sharing stems with different extensions
- **WHEN** files like `report.pdf` and `report.docx` exist in the same folder
- **THEN** each uses a distinct temporary download file name that does not overwrite the other

#### Scenario: Incomplete download cleanup and sync exclusion
- **WHEN** a download is interrupted leaving a temporary file
- **THEN** the sync engine ignores the temporary file and does not upload it to the server as a new user file

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
