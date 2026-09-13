## 1. Frontend — Settings.tsx

- [x] 1.1 Reduce `fitWindowToContent` debounce from 350ms to 80ms
- [x] 1.2 Change `useEffect` dependency from `[adminOpen, storage, fitWindowToContent]` to `[storage, fitWindowToContent]`
- [x] 1.3 Add `maxHeight: 360, overflow: "auto"` to admin user list `Box`
- [x] 1.4 Add `onEntered` and `onExited` callbacks on admin `Collapse` to trigger `fitWindowToContent`

## 2. Backend — lib.rs

- [x] 2.1 Cap `fit_window_to_content` height to the monitor's work area height
- [x] 2.2 Rewrite `show_main_window` to reset size to default (600×720) and restore only position from saved geometry