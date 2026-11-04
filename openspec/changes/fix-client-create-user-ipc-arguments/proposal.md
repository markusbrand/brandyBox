## Why

In the Tauri desktop client (`client-tauri`), the user administration dialog allows administrators to create new users. When submitting the user creation form, `Settings.tsx` invokes the Tauri command `api_create_user` with a payload containing `{ email, first_name, last_name }`.

However, Tauri's `#[tauri::command]` procedural macro converts Rust parameter names (`email`, `first_name`, `last_name`) to `lowerCamelCase` (`email`, `firstName`, `lastName`) for IPC command arguments by default. Tauri's JSON deserializer strictly expects the keys `"firstName"` and `"lastName"`. Because the frontend sends snake_case keys (`first_name`, `last_name`), Tauri fails deserialization immediately with:
`command api_create_user missing required key firstName`.

As a result, creating a new user from the desktop client settings UI always fails with an error and cannot be completed.

## What Changes

- Update `handleCreateUser` in `client-tauri/src/Settings.tsx` to supply camelCase parameter keys (`firstName`, `lastName`) as required by Tauri's IPC deserializer, while also providing `first_name` and `last_name` for defense-in-depth compatibility.
- Ensure the user creation flow correctly completes against the Tauri IPC command interface.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `desktop-client`: Align Tauri IPC command invocation parameters for `api_create_user` with Tauri's command deserialization requirements (`firstName` and `lastName`).

## Impact

- Affected files: `client-tauri/src/Settings.tsx`.
- User-facing impact: Administrators can successfully create new user accounts from the desktop client settings interface without encountering `missing required key firstName` errors.
- No breaking changes or external dependencies added.
