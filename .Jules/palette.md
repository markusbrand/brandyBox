## 2026-08-18 - Add aria-labels to TitleBar
**Learning:** Icon-only buttons for window controls (minimize, maximize, close) in the TitleBar were missing aria-labels, which are critical for screen reader users to identify the purpose of these buttons.
**Action:** Always verify that icon-only buttons have descriptive aria-labels when creating or reviewing components.
## 2025-02-23 - Submit Button and Form Wrappers
**Learning:** Wrapping login inputs in a `<form>` and setting the submit button `type="submit"` enables natural Enter-key submission for users, which is a highly expected behavior and a major accessibility win.
**Action:** When creating forms with Material-UI, default to wrapping them in `<form>` and updating the button types to "submit", and additionally ensure loading states (like `CircularProgress`) are integrated with visual cues (like text changes).
