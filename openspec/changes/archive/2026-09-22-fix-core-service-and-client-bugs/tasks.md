## 1. Backend File Storage & Path Isolation

- [x] 1.1 Allow `+` in `_SAFE_EMAIL` in `backend/app/files/storage.py` and verify via test with `user+tag@example.com`
- [x] 1.2 Exclude `.uploads` directory in `list_files_recursive` and `list_directories_recursive` in `backend/app/files/storage.py` and verify in-progress upload chunks do not appear in `/api/files/list` or `/api/files/folders`
- [x] 1.3 Reject path access into `.uploads` within `resolve_user_path` in `backend/app/files/storage.py` and verify direct download/delete attempts return 400 Bad Request
- [x] 1.4 Add automated pytest regression tests in `backend/tests/` covering email plus-aliasing, `.uploads` exclusion, and path denial

## 2. Desktop Client Runtime & Lifecycle

- [x] 2.1 Update `RunEvent::ExitRequested` handling in `client-tauri/src-tauri/src/lib.rs` to only call `api.prevent_exit()` when `code.is_none()`, enabling Cmd+Q and menu bar Quit
- [x] 2.2 Update `executable_command()` in `client-tauri/src-tauri/src/config.rs` to resolve the absolute binary path using `std::env::current_exe()` across all platforms
- [x] 2.3 Update temporary download path generation in `client-tauri/src-tauri/src/api.rs` to use `.{filename}.tmp_download` and clean up temp files on failure
- [x] 2.4 Add `*.tmp_download` to ignore patterns in `client-tauri/src-tauri/src/sync.rs` so temporary files are never uploaded to the server
- [x] 2.5 Run `cargo test` and verify client unit tests pass with the updated configuration and sync ignore rules
