## Context

In `client-tauri/src-tauri/src/api.rs`, `ApiClient::create_user` currently injects:
```rust
headers.insert("X-E2E-Return-Temp-Password", "1".parse().unwrap());
```
This header was introduced for autonomous E2E testing scenarios to prevent sending real emails and return passwords directly in HTTP responses. However, because it was unconditionally hardcoded into `ApiClient::create_user`, all user creation actions from the desktop application trigger `skip_email = True` in the backend service (`backend/app/users/service.py`).

In the client frontend (`client-tauri/src/Settings.tsx`), `handleCreateUser` calls `invoke("api_create_user", ...)` without inspecting the response:
```tsx
await invoke("api_create_user", {
  email: newUserEmail,
  first_name: newUserFirst,
  last_name: newUserLast,
});
setCreateUserOpen(false);
```
When `temp_password` is returned in the response, it is dropped silently without being displayed.

## Goals / Non-Goals

**Goals:**
- Ensure the production desktop client does not transmit `X-E2E-Return-Temp-Password`, allowing the backend to dispatch welcome emails when SMTP is configured.
- Ensure the desktop client frontend captures any returned `temp_password` from `api_create_user` and displays it to the administrator in a clear modal dialog with a copy button.
- Provide a clear success message when a user is created and the password was delivered via email.

**Non-Goals:**
- Changing backend user creation logic or endpoints (`POST /api/users` response schema already supports optional `temp_password`).
- Adding password reset workflows for existing users.

## Decisions

- **Decision 1: Remove `X-E2E-Return-Temp-Password` from `ApiClient::create_user`**
  - Rationale: The desktop client is a production user-facing application and should not spoof test runner headers. Test runners (like `tests/e2e/e2e_setup.py`) already use the dedicated Python API client with `e2e_return_temp_password=True`.
  - Alternative considered: Adding a checkbox in the UI to toggle email sending - rejected because admins shouldn't need to manually configure backend delivery modes.

- **Decision 2: Modal dialog for temporary password display in Settings.tsx**
  - Rationale: If the backend does not have SMTP configured (or returns a password), the temporary password is only available once in the API response. Closing the modal immediately causes permanent credential loss. Presenting a result modal with a copy-to-clipboard button ensures the administrator can safely copy and transfer credentials to the user.
  - Alternative considered: Displaying the password in an inline alert banner - rejected because users often navigate away or close tabs/windows, whereas a dialog requires acknowledgment and prevents accidental dismissal before copying.

- **Decision 3: Unit test using local mock TCP server**
  - Rationale: `client-tauri/src-tauri/src/api.rs` unit tests can spin up a local TCP listener to verify that `ApiClient::create_user` does not include `X-E2E-Return-Temp-Password` in the transmitted HTTP request headers.

## Risks / Trade-offs

- [Risk] Server without SMTP won't send emails →
  - Mitigation: The server already returns `temp_password` when SMTP is unconfigured; the new UI explicitly presents it to the administrator with instructions to share it.
