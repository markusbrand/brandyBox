## ADDED Requirements

### Requirement: Cross-Platform Home Tilde Path Expansion
The desktop client SHALL expand tilde-prefixed path strings (`~`) relative to the current user's home directory across all platforms, correctly stripping both forward slashes and backslashes.

#### Scenario: Home directory root expansion
- **WHEN** a configured path is `~`, `~/`, or `~\`
- **THEN** the client resolves the path directly to the user's home directory

#### Scenario: Subfolder expansion with Windows backslashes
- **WHEN** a configured path is `~\brandyBox` or `~\\brandyBox` on Windows
- **THEN** the client resolves the path to the `brandyBox` subfolder inside the user's home directory rather than treating it as a drive-root path

#### Scenario: Subfolder expansion with forward slashes
- **WHEN** a configured path is `~/brandyBox`
- **THEN** the client resolves the path to the `brandyBox` subfolder inside the user's home directory

## MODIFIED Requirements

### Requirement: Sync Path Confinement to Local Root
The sync engine SHALL sanitize all file paths and verify that local paths remain strictly confined within the configured sync folder root, resolving both forward slashes and backslashes into native subdirectories.

#### Scenario: Path with leading slashes
- **WHEN** a remote file path has leading slashes (e.g., `/notes.txt`)
- **THEN** the sync engine normalizes the path to `notes.txt` and joins it safely within `local_root`

#### Scenario: Path with backslash separators
- **WHEN** a remote file path contains backslash separators (e.g., `docs\hello.txt` or `\docs\sub\hello.txt`)
- **THEN** the sync engine splits the segments and joins them into the corresponding platform-native subdirectory hierarchy within `local_root`

#### Scenario: Path with directory traversal components
- **WHEN** a file path contains `..` or resolves outside `local_root`
- **THEN** the sync engine rejects the file operation and records a warning without touching files outside `local_root`
