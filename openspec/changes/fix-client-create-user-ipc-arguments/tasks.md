## 1. Implementation

- [x] 1.1 Update `handleCreateUser` in `client-tauri/src/Settings.tsx` to include `firstName` and `lastName` (along with `first_name` and `last_name`) in the `api_create_user` invocation payload

## 2. Verification

- [x] 2.1 Build `client-tauri` frontend (`npm run build`) and verify TypeScript compilation and bundle generation succeed
- [x] 2.2 Run `cargo test` in `client-tauri/src-tauri` and verify all desktop client tests pass
- [x] 2.3 Run `./scripts/run-qa.sh` or relevant verification checks to ensure no regressions
