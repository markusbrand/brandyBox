## 2024-03-22 - [Form submission keyboard a11y]
**Learning:** Found that the "Create User" form in SettingsPage lacked keyboard accessibility (no `<form>` wrapper or `type="submit"` on the button) and a clear loading state for asynchronous calls.
**Action:** Always wrap inputs in a `<form>` and use a submit button when a logical form is present, and show inline loading (e.g. `CircularProgress`) to ensure users can submit smoothly via keyboard and get clear feedback.

## 2024-03-22 - [Dialog Form Keyboard Accessibility]
**Learning:** Found that the "New Folder" dialog in `FilesPage` lacked native `<form>` handling and instead relied on a brittle `onKeyDown` listener on the input to capture the Enter key. It also missed explicit loading indicators on the submit button.
**Action:** Replaced the custom keyboard listener by wrapping `DialogContent` and `DialogActions` in a `<form onSubmit={...}>` with a `type="submit"` button. Added `CircularProgress` on the submit button during async states. Always use native `<form>` elements inside MUI Dialogs for reliable keyboard accessibility and robust loading feedback.
