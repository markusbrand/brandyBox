## Why

Investigation into the Brandy Box backend and desktop client uncovered several concrete, reproducible bugs affecting credentials, sync integrity, and storage consistency:

1. **Expired Refresh Token Infinite Loop**: `credentials::get_stored()` ignores token expiration on macOS/E2E and falls back to expired file credentials unconditionally. When a stored token expires, the background sync loop repeatedly requests token refresh every 10 seconds, encountering HTTP 401 in an endless loop without ever invalidating or clearing the stored credentials.
2. **Path Traversal in Client Sync Engine**: When processing deletions, downloads, and uploads, the sync engine joins paths using `local_root.join(path)`. If a path starts with a leading slash or contains `..`, Rust's `Path::join` treats it as an absolute path or escapes `local_root`, causing file modifications and deletions outside the user's sync directory.
3. **Directory Overwrite on Upload**: In `POST /api/files/upload`, `POST /api/files/upload/init`, and `POST /api/files/upload/finalize`, the server fails to verify whether the upload destination path is already an existing directory. `shutil.move()` moves the temporary file inside the existing directory as an orphaned hidden file, while recording the directory path in the database as a file, causing downloads to fail with HTTP 404 and leaving unlisted orphaned files.
4. **Chunked Upload Missing-Chunk Assembly**: In `POST /api/files/upload/finalize`, chunk assembly sorts all matching glob entries but does not verify chunk index contiguity (`chunk_000000`, `chunk_000001`, ...). If any chunk upload failed, the server stitches together non-contiguous chunks into a corrupt file.

## What Changes

- **Expired Credential Filtering & Cleanup**:
  - Update `credentials::get_stored()` across all platforms to check `!is_jwt_expired(&token)` before returning stored credentials, returning `None` if expired.
  - In `lib.rs: get_valid_access_token()`, explicitly clear stored credentials (`credentials::clear_stored()`) upon receiving a 401 Unauthorized during refresh.
- **Sync Local Path Sanitization**:
  - Introduce safe relative path resolution in `sync.rs` that trims leading slashes, verifies relative component safety, and strictly confines resolved paths within `local_root`.
- **Upload Directory Conflict Prevention**:
  - In `backend/app/files/routes.py`, check whether `target.exists() and target.is_dir()` during `upload_file`, `upload_init`, and `upload_finalize`. Reject with HTTP 409 Conflict if a directory already exists at the destination path.
- **Chunked Upload Integrity & Cleanup**:
  - In `upload_finalize`, enforce strict contiguity of chunk indices from `0` to `total_chunks - 1`, rejecting corrupted uploads with HTTP 400.
  - Ensure temporary upload directories are cleaned up when finalization fails.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `desktop-client`: Expired credential filtering, credential purging on refresh rejection, and sync path confinement within the local sync root.
- `file-storage`: Directory collision rejection on upload endpoints and contiguity verification for chunked uploads.

## Impact

- `client-tauri/src-tauri/src/credentials.rs`: Update `get_stored()` to enforce `is_jwt_expired`.
- `client-tauri/src-tauri/src/lib.rs`: Call `credentials::clear_stored()` when refresh fails with 401.
- `client-tauri/src-tauri/src/sync.rs`: Ensure all local file operations (`delete_local`, `to_download`, `to_upload`) use safe path resolution.
- `backend/app/files/routes.py`: Add directory collision checks and chunk contiguity validation.
- Tests: Add unit tests for expired credential handling, path traversal prevention, directory collision rejection, and chunk contiguity verification.
