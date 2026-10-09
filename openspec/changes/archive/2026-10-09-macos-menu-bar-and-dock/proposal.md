## Why

On macOS, Brandy Box previously appeared as a regular application in the Dock and lacked proper integration into the top-right menu bar (system status bar). Additionally, the status bar icon used a generic/monochrome outline instead of the official Brandy Box "B" logo with sync state indication (as present on Linux), and running the desktop app without a pre-existing Vite dev server resulted in a blank Settings window trying to connect to `localhost:1420`.

## What Changes

- **macOS Menu Bar Accessory & Dock Suppression**: Configured the macOS application to run as an accessory (`LSUIElement = true` and `ActivationPolicy::Accessory`), completely hiding it from the macOS Dock while anchoring it to the menu bar.
- **Top-Right Status Bar Placement**: Configured `NSStatusItem` with persistent autosave positioning (`NSStatusItem Preferred Position brandybox`) to ensure the status item appears visibly on the top-right menu bar away from the MacBook camera notch.
- **Unified Cross-Platform Logo & State Indicators**: Replaced platform-specific monochrome tray stencils with the official Brandy Box logo suite (`icon_synced.png`, `icon_syncing.png`, `icon_error.png`) using `set_icon_as_template(false)` on both macOS and Linux, ensuring 100% visual consistency without touching Linux assets.
- **Embedded Production Frontend**: Configured the build workflow to ensure production builds bundle the compiled frontend assets from `dist/` rather than depending on a local development server on `localhost:1420`.
- **Application Window Restoration & Activation**: Enabled programmatic window activation via `NSApplication activateIgnoringOtherApps` so selecting "Settings" from the tray menu brings the window into active focus.

## Capabilities

### New Capabilities
- `macos-menu-bar-integration`: Defines macOS status item tray integration, Dock icon suppression, official logo sync state visualization, and Settings window activation.

### Modified Capabilities
<!-- None -->

## Impact

- **Rust Backend**: `client-tauri/src-tauri/src/lib.rs` (activation policy, `setup_macos_status_item`, unified icon loading, `activate_macos_app`), `client-tauri/src-tauri/Cargo.toml` (`objc2` macOS dependencies).
- **macOS Configuration**: `client-tauri/src-tauri/Info.plist` (`LSUIElement`), `client-tauri/src-tauri/tauri.conf.json` (`bundle.macOS.infoPlist`).
- **Packaging & Build**: `client-tauri` production build process (`npm run build` + `npx tauri build`).
