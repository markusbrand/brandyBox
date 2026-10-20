## 1. Upfront Sync Plan & Total Work Calculation

- [x] 1.1 Move `to_download` and `to_upload` planning ahead of deletion execution in `client-tauri/src-tauri/src/sync.rs` and verify compilation
- [x] 1.2 Calculate `total_work` as `(to_del_remote.len() + to_del_local.len() + to_download.len() + to_upload.len()) as u64` and log the sync plan before deletions begin
- [x] 1.3 Maintain `base_synced` resolution after local deletions to correctly retain any `failed_local_deletions`

## 2. Regression Testing & Verification

- [x] 2.1 Add unit test in `sync.rs` verifying that modified files are included in total work and progress does not overflow
- [x] 2.2 Run `cargo test` in `client-tauri/src-tauri` and verify all tests pass
- [x] 2.3 Run full project QA suite via `./scripts/run-qa.sh`
