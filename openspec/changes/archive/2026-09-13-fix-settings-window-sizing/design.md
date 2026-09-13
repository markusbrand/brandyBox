## Context

The settings window opens at the saved geometry from the previous session. If the admin usermanagement section was expanded before closing, the saved height is large (~950px). On next open with admin collapsed by default, the window stays at that large height until the frontend re-measures. Additionally, `fit_window_to_content` had no upper bound and the admin user list had no overflow scroll. See `proposal.md` — Why for full motivation.

## Goals / Non-Goals

**Goals:**
- Window opens at a reasonable default height on first show, then resizes to fit collapsed content
- Window height never exceeds the monitor's work area
- Admin user list scrolls internally when many users are present
- Content-based resize feels instant (not delayed by 350ms)

**Non-Goals:**
- No change to user-dragged resize behavior (content-fit always overrides on re-open, as before)
- No persistent user-chosen height (the window always fits content — this is intentional)
- No change to window positioning logic

## Decisions

1. **Reset size to default on show instead of restoring saved geometry** — Previously, `show_main_window` called `restore_window_geometry` which restored both position and size from the last session. The saved size could be very tall if admin had been expanded. The fix: restore only the position, set size to 600×720 (the default), and let the frontend `fitWindowToContent` re-measure immediately. This guarantees a consistent starting size.

2. **Cap height to monitor work area in `fit_window_to_content`** — `win.set_size` with a height exceeding the monitor's work area pushes the window bottom off-screen. The fix: query `win.current_monitor().work_area().size.height` and clamp `h` to that value before calling `set_size`. The window has `decorations: false`, so `set_size` sets the full window size (no OS chrome). The title bar is part of the webview content and is already accounted for in the measurement.

3. **Reduce debounce from 350ms to 80ms** — The 350ms delay was originally for the MUI Collapse animation (300ms). The new approach uses Collapse `onEntered`/`onExited` callbacks for admin toggle and a shorter 80ms debounce for the initial mount / storage-load path. 80ms is imperceptible but prevents thrashing during rapid state changes.

4. **Add `maxHeight: 360, overflow: "auto"` to admin user list** — Without a max-height, a long user list causes `fit_window_to_content` to grow the window unboundedly. 360px accommodates roughly 7 user items before scrolling, and the height cap in Rust prevents screen overflow as a safety net.

## Risks / Trade-offs

- **Position-only restore depends on saved geometry from a prior session** — If geometry was never saved (first run), `show_main_window` falls back to primary-monitor proximity positioning. This is unchanged from the prior behavior.
- **Manual resize by the user is always overridden** — This was already the case (fit_window_to_content fires on mount and overrides). No regression.
- **80ms debounce may race with Collapse animation** — The `onEntered`/`onExited` callback is the authoritative resize trigger for admin toggles, so the 80ms debounce is only relevant for storage-load and mount. If the race fires a redundant `invoke`, the second call is a no-op (same dimensions) or a minor adjustment.