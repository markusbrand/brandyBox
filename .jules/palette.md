## 2024-03-22 - [Form submission keyboard a11y]
**Learning:** Found that the "Create User" form in SettingsPage lacked keyboard accessibility (no `<form>` wrapper or `type="submit"` on the button) and a clear loading state for asynchronous calls.
**Action:** Always wrap inputs in a `<form>` and use a submit button when a logical form is present, and show inline loading (e.g. `CircularProgress`) to ensure users can submit smoothly via keyboard and get clear feedback.
