## 1. Unit Testing and Reproduction

- [x] 1.1 Add regression unit test `delete_remote_then_sync_removes_locally_not_upload` in `client-tauri/src-tauri/src/sync.rs` and verify it fails or exposes candidate inclusion before the fix
- [x] 1.2 Update candidate selection in `client-tauri/src-tauri/src/sync.rs` to exclude `to_del_local_set` and verify the test passes

## 2. Verification and Quality Assurance

- [x] 2.1 Run full cargo test suite in `client-tauri/src-tauri` and verify all tests pass cleanly
- [x] 2.2 Verify whole project QA with `cargo test` and `pytest`
