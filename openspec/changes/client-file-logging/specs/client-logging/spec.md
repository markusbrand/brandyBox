## Purpose

Provides persistent disk logging, log rotation, and diagnostic inspection capabilities for the Brandy Box desktop client across all supported platforms.

## ADDED Requirements

### Requirement: Persistent disk logging
The desktop client SHALL write application logs to a dedicated, platform-standard log directory on the host operating system.

#### Scenario: App logs write to disk on startup and during operations
- **WHEN** the desktop application launches or executes operations
- **THEN** log events containing timestamps, log levels, target modules, and message bodies are written to a persistent log file on disk.

### Requirement: Log rotation and size limits
The desktop client SHALL enforce file rotation and size limits to prevent unbounded disk usage by log files.

#### Scenario: Active log exceeds size limit
- **WHEN** the active log file reaches its size threshold of 5 megabytes
- **THEN** the system rotates the log file and retains at most 5 historical log files, pruning older files.

### Requirement: Access logs from user interface
The desktop client SHALL provide a mechanism in the Settings interface allowing the user to open the application log directory in the system file manager.

#### Scenario: User requests log folder from settings
- **WHEN** the user clicks the "Open Logs Folder" action in the desktop client settings
- **THEN** the application reveals the log directory in the operating system's native file manager (Finder on macOS).

### Requirement: Error capture for sync operations
The desktop client SHALL record detailed diagnostic information, including underlying error causes, when background sync cycles or API requests fail.

#### Scenario: Sync operation encounters an error
- **WHEN** a background sync cycle fails due to network timeout, HTTP error, or local filesystem issue
- **THEN** the client logs the failure description and underlying causal chain at WARN or ERROR level to the persistent log file.
