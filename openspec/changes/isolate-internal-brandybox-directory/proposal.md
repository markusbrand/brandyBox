## Why

When users upload a custom background image in the web interface, the backend stores it in an internal user folder at `.brandybox/content-bg.<ext>`. While `.uploads` was previously isolated from user-visible file listings and direct path resolution, `.brandybox` was omitted from the storage exclusion filters.

As a result:
1. `GET /api/files/list` returns `.brandybox/content-bg.<ext>` as a user file.
2. `GET /api/files/folders` returns `.brandybox` as an empty or browsable user folder.
3. Desktop sync clients (`client-tauri`) discover `.brandybox/content-bg.<ext>` in remote file listings and download it onto the user's local filesystem.
4. If a user deletes the local `.brandybox` folder on their computer, desktop sync calls `DELETE /api/files/delete?path=.brandybox/...`, wiping the user's web background image from the server.
5. Users can read, overwrite, or delete internal background images directly via standard file API endpoints (`/api/files/download`, `/api/files/upload`, `/api/files/delete`).

## What Changes

- Update `backend/app/files/storage.py`:
  - Define `INTERNAL_DIRS = {".uploads", ".brandybox"}`.
  - Enforce rejection in `resolve_user_path` when accessing any directory in `INTERNAL_DIRS`.
  - Filter out `INTERNAL_DIRS` in `list_files_recursive` and `list_directories_recursive`.
- Update `backend/app/users/background_image.py`:
  - Resolve `.brandybox` directly using `user_base_path(email) / _REL_FOLDER` rather than `resolve_user_path(email, _REL_FOLDER)`.
- Update `client-tauri/src-tauri/src/sync.rs`:
  - Ignore `.brandybox` and `.uploads` in `is_ignored` for defense-in-depth.
- Add unit and integration tests verifying `.brandybox` exclusion and path resolution rejection.

## Capabilities

### Modified Capabilities
- `file-storage`: Enforce isolation for all internal directories (including `.brandybox` and `.uploads`) in file listings, folder listings, and path resolution.
- `desktop-client`: Prevent desktop client from syncing internal server directories (`.brandybox`, `.uploads`).

## Impact

- **Affected code**: `backend/app/files/storage.py`, `backend/app/users/background_image.py`, `client-tauri/src-tauri/src/sync.rs`
- **APIs**: `GET /api/files/list` and `GET /api/files/folders` no longer include `.brandybox`. Path resolution rejects direct access to `.brandybox`.
- **Dependencies**: None.
- **Behavior**: Background images continue to work seamlessly in the web UI, but `.brandybox` is completely hidden from file browsers and desktop sync.
