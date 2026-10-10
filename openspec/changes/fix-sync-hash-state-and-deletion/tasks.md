## 1. Sync Planning and 3-Way Hash Reconciliation

- [x] 1.1 Implement 3-way hash comparison in `to_upload` and `to_download` planning within `client-tauri/src-tauri/src/sync.rs` and verify with unit tests
- [x] 1.2 Verify disk hash instead of checking stale `state.file_hashes` in the download execution loop in `sync.rs` and verify with unit tests

## 2. Hash Cache Consistency and Deletion Resilience

- [x] 2.1 Update `state.file_hashes` upon successful file upload in `sync.rs` and verify with unit tests
- [x] 2.2 Prune deleted file entries from `state.file_hashes` during `to_del_local` and `to_del_remote` in `sync.rs` and verify with unit tests
- [x] 2.3 Handle local deletion errors in `to_del_local`, retaining failed paths in `state.paths` and recording diagnostic error events and warnings, and verify with unit tests

## 3. Verification and Testing

- [x] 3.1 Run full Rust test suite (`cargo test`) in `client-tauri/src-tauri` and verify all tests pass
- [x] 3.2 Run backend unit and integration tests to ensure no regressions
