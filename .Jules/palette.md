## 2026-08-18 - Add aria-labels to TitleBar
**Learning:** Icon-only buttons for window controls (minimize, maximize, close) in the TitleBar were missing aria-labels, which are critical for screen reader users to identify the purpose of these buttons.
**Action:** Always verify that icon-only buttons have descriptive aria-labels when creating or reviewing components.
## 2026-08-25 - Add loading states for async operations
**Learning:** Loading states for async form submissions (like login) give immediate feedback to users and prevent duplicate submissions. This is an important interaction improvement.
**Action:** Always verify that form submission buttons show a loading indicator or state (e.g. CircularProgress) and descriptive text when an async action is active.
