## 1. Backend Implementation & Tests

- [x] 1.1 Add unit tests in `backend/tests/test_storage.py` asserting `.brandybox` rejection and exclusion from file and folder listings
- [x] 1.2 Add integration test in `backend/tests/test_web_features.py` asserting background image upload does not leak into `/api/files/list` or `/api/files/folders`
- [x] 1.3 Update `INTERNAL_DIRS` in `backend/app/files/storage.py` and enforce in `resolve_user_path`, `list_files_recursive`, and `list_directories_recursive`
- [x] 1.4 Update `backend/app/users/background_image.py` to use `user_base_path`

## 2. Desktop Client Implementation & Tests

- [x] 2.1 Update `is_ignored` in `client-tauri/src-tauri/src/sync.rs` to ignore `.brandybox` and `.uploads`
- [x] 2.2 Add unit test in `client-tauri/src-tauri/src/sync.rs` verifying `.brandybox` and `.uploads` are ignored

## 3. Verification & Quality Assurance

- [x] 3.1 Run `pytest backend` and verify all tests pass
- [x] 3.2 Run `cargo test` in `client-tauri/src-tauri` and verify all tests pass
- [ ] 3.3 Create git commit and pull request
