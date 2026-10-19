## Why

When an administrator creates a new user through the desktop client (Tauri UI), the desktop client unexpectedly includes the test header `X-E2E-Return-Temp-Password: 1` on the `POST /api/users` request. This causes the backend to bypass email delivery (`skip_email = True`), preventing the user from ever receiving their initial password email—even when SMTP is fully configured and operational.

Simultaneously, the backend responds with the generated temporary password in the JSON payload (`temp_password`), but the desktop client's settings UI completely ignores the API response and immediately closes the dialog without displaying the temporary password or offering a way to copy it. As a result, the newly created user cannot receive an email, the administrator cannot view or copy the generated password, and the account is rendered completely inaccessible. Furthermore, in environments where SMTP is intentionally not configured (or email delivery is not used), the returned temporary password is also discarded and lost.

## What Changes

- In `client-tauri/src-tauri/src/api.rs`, remove the hardcoded `X-E2E-Return-Temp-Password: 1` request header from `ApiClient::create_user`. Normal client user creation requests will allow the backend to send welcome emails with temporary passwords when SMTP is configured.
- In `client-tauri/src-tauri/src/api.rs`, add unit test coverage verifying that `create_user` does not include `X-E2E-Return-Temp-Password` in request headers.
- In `client-tauri/src/Settings.tsx`, update `handleCreateUser` to inspect the response returned by `api_create_user`:
  - When `temp_password` is present in the response (e.g. SMTP not configured on server or password returned), display a dedicated user creation success dialog showing the created user email, the generated temporary password, a button to copy the password to the clipboard, and an explanatory notice to securely share it with the user.
  - When `temp_password` is absent (indicating the backend emailed the credentials), display an informative success banner confirming that the user was created and the invitation email was sent.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `desktop-client`: Require the desktop client to omit test password headers during administrative user creation, allowing the server to deliver password emails when configured, and require the client settings UI to capture and display generated temporary passwords when returned by the API.

## Impact

- **Affected code**: `client-tauri/src-tauri/src/api.rs`, `client-tauri/src/Settings.tsx`
- **APIs**: No backend API contract changes (`POST /api/users` already returns `UserCreateResponse` with optional `temp_password`).
- **Dependencies**: No new dependencies.
- **Behavior**: User accounts created from the desktop client will reliably receive email invitations when SMTP is configured, and administrators will be shown temporary passwords with copy-to-clipboard functionality when SMTP is not configured.
