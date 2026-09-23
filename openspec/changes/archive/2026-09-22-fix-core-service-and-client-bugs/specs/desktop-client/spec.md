## Purpose

Manages the native desktop client lifecycle, application termination controls, autostart integration, and robust file download synchronization.

## ADDED Requirements

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
