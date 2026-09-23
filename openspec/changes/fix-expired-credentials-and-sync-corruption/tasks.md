## 1. Desktop Client Credential Handling & Refresh Recovery

- [x] 1.1 Enforce `!is_jwt_expired(&token)` across all platforms in `client-tauri/src-tauri/src/credentials.rs: get_stored()` and verify with a unit test.
- [x] 1.2 In `client-tauri/src-tauri/src/lib.rs: get_valid_access_token()`, purge credentials via `credentials::clear_stored()` when token refresh returns HTTP 401 Unauthorized.

## 2. Desktop Sync Path Confinement

- [x] 2.1 Implement `safe_local_path` helper in `client-tauri/src-tauri/src/sync.rs` and apply it to `to_del_local`, `to_download`, and `to_upload`. Verify with unit tests against leading slashes and `..` traversal.

## 3. Backend Upload Directory Collision & Chunk Contiguity

- [x] 3.1 In `backend/app/files/routes.py`, validate destination paths in `upload_file`, `upload_init`, and `upload_finalize` to reject collisions with existing directories with HTTP 409 Conflict.
- [x] 3.2 In `backend/app/files/routes.py: upload_finalize`, enforce contiguous chunk indices (`0` through `N-1`) and clean up temporary files on error. Verify with pytest.

## 4. Verification and Integration

- [x] 4.1 Run client unit tests (`cargo test`) and backend tests (`pytest backend/tests`) to ensure all test suites pass.
