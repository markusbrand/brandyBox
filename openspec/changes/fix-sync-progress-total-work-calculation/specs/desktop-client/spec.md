## ADDED Requirements

### Requirement: Comprehensive Sync Progress Accounting
The desktop client synchronization engine SHALL calculate total planned work by accounting for all deletions, downloads (both newly added and modified remote files), and uploads (both newly added and modified local files) before executing file operations, and SHALL report progress where completed count is strictly bounded by total work.

#### Scenario: Synchronization with modified local files
- **WHEN** existing files are modified locally while no new files are created
- **THEN** total planned work equals the count of modified files to upload and progress reflects actual file upload progress rather than reporting zero total work

#### Scenario: Synchronization with modified remote files
- **WHEN** existing files are modified on the server
- **THEN** total planned work includes all modified files to download and progress counts do not exceed total work

#### Scenario: Mixed additions, modifications, and deletions
- **WHEN** a sync run contains a combination of deletions, new additions, and file modifications
- **THEN** total planned work matches the sum of server deletions, local deletions, planned downloads, and planned uploads, and emitted progress remains bounded between 0 and total work
