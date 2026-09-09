## 2026-08-18 - Add aria-labels to TitleBar
**Learning:** Icon-only buttons for window controls (minimize, maximize, close) in the TitleBar were missing aria-labels, which are critical for screen reader users to identify the purpose of these buttons.
**Action:** Always verify that icon-only buttons have descriptive aria-labels when creating or reviewing components.

## 2026-08-25 - Add loading states for async operations
**Learning:** Loading states for async form submissions (like login) give immediate feedback to users and prevent duplicate submissions. This is an important interaction improvement.
**Action:** Always verify that form submission buttons show a loading indicator or state (e.g. CircularProgress) and descriptive text when an async action is active.

## 2025-02-23 - Submit Button and Form Wrappers
**Learning:** Wrapping login inputs in a `<form>` and setting the submit button `type="submit"` enables natural Enter-key submission for users, which is a highly expected behavior and a major accessibility win.
**Action:** When creating forms with Material-UI, default to wrapping them in `<form>` and updating the button types to "submit", and additionally ensure loading states (like `CircularProgress`) are integrated with visual cues (like text changes).

## 2026-08-31 - Add confirmation dialog for destructive actions
**Learning:** Destructive actions such as deleting a user account were missing a confirmation step in the `web/src/pages/SettingsPage.tsx`, unlike file deletions which correctly utilized `window.confirm`.
**Action:** When creating or reviewing components with destructive actions (e.g., delete, remove), always verify that a confirmation dialog (like `window.confirm`) is implemented to prevent accidental data loss and improve safety.

## 2026-09-01 - Native Form Submission in Dialogs
**Learning:** Dialogs with user inputs (such as Appearance, Change Password, Create User, New Folder) should be wrapped in native `<form onSubmit={...}>` with primary action buttons typed as `type="submit"`. This enables native Enter-key submission and accessible form semantics across browsers and operating systems.
**Action:** Always wrap input containers within Dialogs inside `<form>` elements and provide `type="submit"` on confirmation buttons.
## 2026-09-02 - Add loading states for background image upload
**Learning:** Loading states for async operations like uploading images provide critical feedback. Missing loading states on file inputs can lead to confusion if the upload is slow, as the user has no visual cue that processing is occurring.
**Action:** When adding or reviewing file upload forms, always verify that the submit/upload button transitions to a disabled, loading state with clear text (e.g., "Uploading...") and an indicator (e.g., CircularProgress) while the upload is in progress. Also disable the hidden `<input type="file">` to prevent concurrent selections.
