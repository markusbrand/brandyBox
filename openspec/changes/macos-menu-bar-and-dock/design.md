## Context

See proposal.md. On macOS, Tauri v2 applications run as standard foreground applications by default, creating a Dock icon and relying on default `NSStatusItem` behavior. Additionally, Tauri's default macOS tray configuration uses monochrome template mode, which strips colors from rich icons.

## Goals / Non-Goals

**Goals:**
- Eliminate the app from the macOS Dock completely (`background only: true`).
- Position the menu bar icon into the visible top-right status item area ($x \approx 1105$) away from the MacBook notch.
- Ensure the menu bar icon looks identical to the official Brandy Box "B" logo on Garuda Linux across all states (synced, syncing, error).
- Ensure the production binary embeds the frontend web assets, avoiding `localhost:1420` connection failures.
- Activate the application and focus the Settings window when selected from the tray menu.

**Non-Goals:**
- Altering Linux tray behavior or modifying Linux icon assets.
- Changing app behavior on Windows.

## Decisions

### 1. Dock Icon Suppression via Info.plist & ActivationPolicy
- **Decision**: Configure `LSUIElement = true` in `Info.plist` (registered via `tauri.conf.json` under `bundle.macOS.infoPlist`) and call `app.set_activation_policy(tauri::ActivationPolicy::Accessory)` during app setup.
- **Rationale**: This is the canonical Apple guideline for accessory/menu-bar-only utilities. It ensures the app does not appear in the Dock or Cmd+Tab app switcher.
- **Alternative Considered**: Hiding window on close without accessory policy; rejected because the Dock icon remained visible.

### 2. Status Item Positioning via NSUserDefaults & autosaveName
- **Decision**: Seed `NSStatusItem Preferred Position brandybox` (value `320.0`) in `NSUserDefaults` and dynamically set `autosaveName = "brandybox"` on the `NSStatusBarWindow`'s status item using `objc2`.
- **Rationale**: On MacBooks with display notches, status items default to positions that often get clipped behind the notch if too many status items exist. Setting the preferred position places it on the right side of the menu bar ($x \approx 1105$), while `autosaveName` enables user Cmd-drag customization.
- **Alternative Considered**: Leaving positioning to macOS defaults; rejected because the icon was hidden behind the notch on initial run.

### 3. Universal Logo & Full-Color Rendering
- **Decision**: Unify `ICON_SYNCED_BYTES`, `ICON_SYNCING_BYTES`, and `ICON_ERROR_BYTES` across all platforms to point to `icon_synced.png`, `icon_syncing.png`, and `icon_error.png`, and set `icon_as_template(false)`.
- **Rationale**: The `tray-icon` crate automatically downscales PNG assets to 18pt menu bar height on macOS while preserving high-DPI Retina fidelity. With `icon_as_template(false)`, macOS retains the full branding colors (blue, orange, red) identical to Garuda Linux.
- **Alternative Considered**: Rendering a custom vector monochrome stencil; rejected because the user explicitly requires the official colorful "B" logo.

### 4. Build Pipeline with Embedded Frontend
- **Decision**: Build the web UI via `npm run build` into `dist/` before running release compilation via `npx tauri build --no-bundle`.
- **Rationale**: Tauri v2 only embeds local assets when building in production mode with built frontend artifacts. Without this, the binary attempts to connect to `http://localhost:1420`, resulting in a blank Settings window when no dev server is active.

## Risks / Trade-offs

- **[Risk] ARM64 ABI Calling Convention Crashes**: Declaring raw variadic `objc_msgSend` on ARM64 macOS passes arguments in stack slots rather than registers, causing SIGSEGV.
  - **Mitigation**: Use the `objc2` crate's `msg_send!` macro which generates correct non-variadic prototypes for Apple Silicon.
- **[Risk] Linux Regressions**: Changes to icon loading or tray configuration breaking the Garuda Linux desktop client.
  - **Mitigation**: Preserved the original Linux icon asset files without modification and maintained identical runtime parameters.
