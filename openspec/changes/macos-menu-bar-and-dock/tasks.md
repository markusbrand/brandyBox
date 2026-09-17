## 1. macOS Dock Suppression & Activation Policy

- [x] 1.1 Add `LSUIElement = true` via `client-tauri/src-tauri/Info.plist` and configure `tauri.conf.json` `bundle.macOS.infoPlist`
- [x] 1.2 Set `ActivationPolicy::Accessory` in `client-tauri/src-tauri/src/lib.rs` and verify with `osascript` that process reports `background only: true` without appearing in Dock

## 2. Menu Bar Placement & Window Activation

- [x] 2.1 Implement `setup_macos_status_item` using `objc2::msg_send!` to configure `NSStatusItem Preferred Position brandybox` (320.0) and `autosaveName = "brandybox"` away from MacBook camera notch
- [x] 2.2 Implement `activate_macos_app` to activate the application and bring Settings window to front upon menu selection
- [x] 2.3 Prevent background process exit on window close via `tauri::RunEvent::ExitRequested { api, .. } => api.prevent_exit()`

## 3. Logo Consistency & Cross-Platform Parity

- [x] 3.1 Unify `ICON_SYNCED_BYTES`, `ICON_SYNCING_BYTES`, and `ICON_ERROR_BYTES` in `lib.rs` to use official Brandy Box `icon_synced.png`, `icon_syncing.png`, and `icon_error.png`
- [x] 3.2 Configure `icon_as_template(false)` on tray initialization and status updates so full color branding is displayed on macOS
- [x] 3.3 Verify original icon assets in `client-tauri/src-tauri/icons/` remain completely unchanged for Linux parity

## 4. Production Frontend Embedding & Verification

- [x] 4.1 Compile frontend production assets with `npm run build` and build release binary via `npx tauri build --no-bundle`
- [x] 4.2 Deploy compiled binary to `/Applications/Brandy Box.app/Contents/MacOS/brandybox`
- [x] 4.3 Verify menu bar icon displays official blue "B" (synced) and orange "B" (syncing)
- [x] 4.4 Verify Settings window opens without `localhost:1420` connection error
