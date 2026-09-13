## Why

After booting the PC and opening the settings window for the first time, it extends to the very bottom of the screen instead of fitting its collapsed content. Expanding and collapsing the admin usermanagement section temporarily fixes the size. Additionally, when the admin usermanagement section is expanded with many users, the window grows beyond the screen because there is no scrollbar, and the window height is not capped to the display work area.

## What Changes

- Reset window to default size (600×720) in `show_main_window` instead of restoring the potentially large saved geometry
- Cap `fit_window_to_content` height to the monitor's work area so the window never overflows the screen
- Reduce the frontend debounce from 350ms to 80ms so the content-based resize happens almost instantly after opening
- Add `maxHeight: 360` and `overflow: auto` to the admin user list container so many users produce a scrollbar instead of growing the window
- Trigger `fitWindowToContent` via Collapse `onEntered`/`onExited` callbacks so the window re-sizes after the animation completes

## Capabilities

### New Capabilities

None – this is a behavioral fix with no new spec-level contract.

### Modified Capabilities

None – no existing specs are affected.

## Impact

- **Affected files**:
  - `client-tauri/src-tauri/src/lib.rs` — `show_main_window` and `fit_window_to_content` rewritten
  - `client-tauri/src/Settings.tsx` — debounce reduced, admin list scroll added, Collapse callbacks wired
- **No API changes**. No dependency changes. No breaking changes.
- **GitHub Issue**: Not applicable (no GitHub issue created for this fix)