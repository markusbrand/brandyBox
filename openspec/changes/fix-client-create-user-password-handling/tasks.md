## 1. Client API Header Correction

- [x] 1.1 Remove `X-E2E-Return-Temp-Password` header insertion in `client-tauri/src-tauri/src/api.rs` and verify `cargo test` passes
- [x] 1.2 Add unit test in `client-tauri/src-tauri/src/api.rs` asserting `create_user` does not send `X-E2E-Return-Temp-Password` and verify with `cargo test`

## 2. Desktop Settings UI Password Display

- [x] 2.1 Update `handleCreateUser` and user creation dialog in `client-tauri/src/Settings.tsx` to handle `temp_password` and email confirmation
- [x] 2.2 Add temporary password modal dialog with copy-to-clipboard functionality in `client-tauri/src/Settings.tsx`
- [x] 2.3 Verify `npm run build` in `client-tauri` succeeds

## 3. QA and Verification

- [x] 3.1 Run `./scripts/run-qa.sh` to ensure all tests across backend, client-tauri, web, and docs pass
