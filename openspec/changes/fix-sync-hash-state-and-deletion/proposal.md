## Why

The desktop sync engine contains subtle logic flaws that can cause silent synchronization stalls, data divergence under clock skew, and accidental resurrection of deleted files:
1. In `to_upload`, `*local_mtime <= r.mtime` early-returns before comparing SHA-256 hashes, preventing locally modified files from uploading if the local clock lags behind the server clock (or if older timestamps were preserved).
2. In the download execution loop, `state.file_hashes.get(path) == Some(hash)` checks the previous sync record rather than the actual file on disk, prematurely skipping downloads when the disk file has changed.
3. Successful uploads never update `state.file_hashes`, leaving the client unaware of current file hashes.
4. Failed local file deletions in `to_del_local` silently ignore filesystem errors and remove the file from `state.paths`, causing the file to be treated as a brand new local file and re-uploaded (resurrected) to the server on the next sync cycle.

## What Changes

- **Clock Skew Resilient Hash Reconciliation**: Implement 3-way hash comparison (`state.file_hashes`, local disk hash, and server hash) in `to_upload` and `to_download`. When local content changes while the server content matches `state.file_hashes`, the file is marked for upload regardless of timestamp order.
- **Accurate Download Disk Verification**: Avoid skipping downloads based on stale `state.file_hashes`; verify the actual file hash on disk when deciding whether a download is redundant.
- **Upload Hash State Tracking**: Update `state.file_hashes` with the computed SHA-256 hash immediately upon successful upload.
- **State Pruning on Deletion**: Remove deleted file entries from `state.file_hashes` when files are removed on the server or locally.
- **Failed Local Deletion Retention & Warning**: If `std::fs::remove_file` fails during `to_del_local`, retain the path in `state.paths`, enqueue a diagnostic error event, and include a warning in the sync summary to prevent resurrection on subsequent sync cycles.

## Capabilities

### Modified Capabilities
- `desktop-client`: Add requirements for clock-skew resilient hash synchronization, upload hash state caching, and prevention of remote resurrection on failed local deletions.

## Impact

- `client-tauri/src-tauri/src/sync.rs`: Updates to candidate planning (`to_download`, `to_upload`), download loop verification, upload hash caching, and local deletion error handling.
- No breaking API changes or database migrations.
