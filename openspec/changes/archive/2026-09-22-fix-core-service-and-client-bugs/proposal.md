## Why

Exploration of the codebase revealed several concrete, reproducible bugs in the backend storage service and client desktop runtime:
1. The macOS client ignores `Cmd+Q` and the menu bar "Quit Brandy Box" item due to an unconditional `api.prevent_exit()` call.
2. User email addresses containing `+` (such as Gmail aliases `user+tag@gmail.com`) are rejected by the backend storage path sanitizer, returning HTTP 500 on file listing and HTTP 400 on uploads.
3. In-progress chunked upload directories (`.uploads`) and raw chunk files are exposed in `GET /api/files/list` and `GET /api/files/folders`, leaking internal files and causing desktop sync clients to download incomplete chunks.
4. The macOS autostart LaunchAgent plist uses a relative binary name (`BrandyBox`) instead of the absolute path to the executable, causing launchd to fail with `posix_spawn: No such file or directory`.
5. File download temp path derivation replaces the existing extension with `.tmp_download`, causing immediate truncation and deletion of files named `*.tmp_download`, name collisions between files sharing stems, and re-uploading of incomplete downloads.

Fixing these issues restores expected desktop client lifecycle controls, enables valid plus-addressed user accounts to use storage, prevents sync corruption from leaking upload chunks, repairs macOS launch-at-login, and protects download integrity.

## What Changes

- **Desktop Client Exit Lifecycle**: Update `RunEvent::ExitRequested` handling in `lib.rs` to only prevent exit when `code.is_none()` (closing the last window), allowing explicit quit actions (`code.is_some()`) like `Cmd+Q` and menu bar "Quit Brandy Box" to terminate the app.
- **Email Path Sanitization**: Update `_SAFE_EMAIL` in `backend/app/files/storage.py` to allow `+` characters in user email folder names, matching RFC 5322 and Pydantic `EmailStr`.
- **Upload Directory & Chunk Isolation**: Exclude `.uploads` from recursive directory and file scanning in `backend/app/files/storage.py`, and disallow resolving paths within `.uploads` in `resolve_user_path`.
- **macOS Autostart LaunchAgent Absolute Path**: Update `executable_command()` in `client-tauri/src-tauri/src/config.rs` to use `std::env::current_exe()` across all platforms so `launchd` receives an absolute executable path.
- **Download Temp File Safety & Ignore Rules**: Change temp download paths in `client-tauri/src-tauri/src/api.rs` to preserve original file extensions (e.g. `.{filename}.tmp_download`), clean up temp files on error, and ensure `*.tmp_download` patterns are ignored by the sync engine in `client-tauri/src-tauri/src/sync.rs`.

## Capabilities

### New Capabilities
- `file-storage`: Storage directory isolation, safe path sanitization for email addresses with `+`, and exclusion of internal upload scratch spaces from public listings.
- `desktop-client`: Native client lifecycle, quit handling on macOS, reliable launch-at-login autostart configuration, and resilient temporary download file management.

### Modified Capabilities
<!-- None: No existing specs cover file storage or desktop client lifecycle. -->

## Impact

- `backend/app/files/storage.py`: Regex pattern update for email safety, path resolution guard for `.uploads`, and directory walker filter.
- `client-tauri/src-tauri/src/lib.rs`: Event loop handling for `RunEvent::ExitRequested`.
- `client-tauri/src-tauri/src/config.rs`: `executable_command` path resolution using `current_exe()`.
- `client-tauri/src-tauri/src/api.rs`: `download_file_to_path` temp file naming.
- `client-tauri/src-tauri/src/sync.rs`: `is_ignored` filter for temporary download files.
- Tests: Added regression tests for backend storage and client logic.
