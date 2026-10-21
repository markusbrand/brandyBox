## Why

The desktop client background sync loop (`spawn_background_sync_loop`) runs periodic synchronization in the background but omits reporting telemetry ping to `POST /api/clients/ping` upon completion. Consequently, the server's operator diagnostics (`GET /api/admin/clients`) remain stale during normal unattended operation. In addition, when background synchronization runs or when the user opens the Settings window while synchronization is active, the desktop Settings UI ignores the `"syncing"` status event and query state, causing the UI to show an idle state and allowing users to trigger concurrent manual sync attempts that fail with a confusing warning.

## What Changes

- Update `spawn_background_sync_loop` in `client-tauri/src-tauri/src/lib.rs` to invoke `client.client_ping(Some(sync_ok), Some(last_sync_at))` upon completion of each background sync pass, aligning background sync with manual `run_sync` telemetry reporting.
- Update `client-tauri/src/Settings.tsx` to handle the `"syncing"` status in both the `sync-status` event listener and the initial `get_sync_status` call on mount. When syncing is active, `syncing` is set to `true`, clearing previous errors or warnings, disabling duplicate sync triggers, and activating progress polling.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `desktop-client`: Background sync telemetry reporting to server and UI synchronization state reflecting active sync operations.

## Impact

- `client-tauri/src-tauri/src/lib.rs`: Background sync loop records telemetry via `client_ping`.
- `client-tauri/src/Settings.tsx`: Settings window correctly tracks syncing state and progress across background and manual runs.
- Server telemetry / operator diagnostics: Correctly reflects client activity for unattended desktop clients without requiring manual sync triggers.
