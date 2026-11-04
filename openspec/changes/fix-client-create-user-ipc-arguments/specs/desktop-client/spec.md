## ADDED Requirements

### Requirement: Desktop Client User Creation IPC Compatibility
The desktop client settings UI SHALL supply user creation arguments adhering to Tauri's lowerCamelCase IPC parameter conventions (`firstName` and `lastName`) when invoking the `api_create_user` command.

#### Scenario: Submitting new user form from settings
- **WHEN** an administrator enters email, first name, and last name and submits the user creation dialog
- **THEN** the frontend invokes `api_create_user` with `firstName` and `lastName` matching the deserialization contract of the Tauri command handler
- **AND** the command does not fail with `missing required key firstName` or parameter deserialization errors
