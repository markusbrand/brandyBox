## 1. Test Suite & Reproduction Verification

- [x] 1.1 Add unit tests in `backend/tests/test_files_routes.py` covering path normalization for leading slashes, backslashes, and redundant separators
- [x] 1.2 Add integration tests in `backend/tests/test_upload_streaming.py` asserting that uploads with leading slashes produce matching hashes in `GET /api/files/list` and are deleted cleanly from `file_hashes` on file deletion

## 2. Path Normalization & Hash Synchronization Implementation

- [x] 2.1 Update `_normalize_path_param` in `backend/app/files/routes.py` to canonicalize slashes, remove leading/trailing slashes, and strip redundant segments
- [x] 2.2 Update `upload_init` in `backend/app/files/routes.py` to save the canonicalized relative path
- [x] 2.3 Update `upload_file` and `upload_finalize` in `backend/app/files/routes.py` to record hashes using canonical relative paths and return canonical paths in API responses
- [x] 2.4 Update `upload_file` and `upload_finalize` in `backend/app/files/routes.py` to clamp `storage_used_bytes` to non-negative values
- [x] 2.5 Update `delete_file` in `backend/app/files/routes.py` to use canonical relative paths for hash deletion and ensure dangling hash records are deleted

## 3. Verification & Quality Assurance

- [x] 3.1 Run full backend test suite (`pytest backend`) and verify all tests pass
- [x] 3.2 Run Tauri desktop client tests (`cargo test` in `client-tauri/src-tauri`) to verify end-to-end compatibility
