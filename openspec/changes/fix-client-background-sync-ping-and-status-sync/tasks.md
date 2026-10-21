## 1. Background Sync Telemetry Reporting

- [x] 1.1 In `client-tauri/src-tauri/src/lib.rs`, capture sync outcome and invoke `client.client_ping(Some(sync_ok), Some(last_sync_at))` in `spawn_background_sync_loop`, verifying compilation with `cargo check`
- [x] 1.2 Run `cargo test` in `client-tauri/src-tauri` and verify all tests pass

## 2. Desktop Settings UI Active Sync Synchronization

- [x] 2.1 In `client-tauri/src/Settings.tsx`, handle `status === "syncing"` in the `sync-status` event listener and in initial `get_sync_status` invoke to set `syncing: true` and clear previous error and warning banners
- [x] 2.2 Run `npm run build` in `client-tauri` and verify build succeeds without TypeScript or Vite errors
