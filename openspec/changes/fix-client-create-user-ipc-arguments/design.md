## Context

See `proposal.md` for background and problem statement. In `client-tauri/src/Settings.tsx`, `handleCreateUser` calls `invoke("api_create_user", { email: newUserEmail, first_name: newUserFirst, last_name: newUserLast })`.
In `client-tauri/src-tauri/src/lib.rs`, `api_create_user` is defined as:
```rust
#[tauri::command]
fn api_create_user(email: String, first_name: String, last_name: String) -> Result<serde_json::Value, String>
```
Tauri's procedural macro converts Rust parameter names to `lowerCamelCase` when deserializing incoming JSON arguments unless explicitly configured with `rename_all`. As a result, Tauri expects `firstName` and `lastName`. Because `Settings.tsx` supplies `first_name` and `last_name`, Tauri IPC throws a deserialization error (`missing required key firstName`) and aborts the command before invoking the backend API.

## Goals / Non-Goals

**Goals:**
- Fix `handleCreateUser` in `Settings.tsx` to supply `firstName` and `lastName` to satisfy Tauri's IPC deserializer.
- Provide both `firstName`/`lastName` and `first_name`/`last_name` in the invocation payload to maintain full forward/backward compatibility.
- Ensure the desktop client build and static analysis succeed without regressions.

**Non-Goals:**
- Changing backend FastAPI HTTP endpoints (FastAPI expects snake_case, which `api.rs` already formats in `CreateUserBody`).
- Altering the user creation modal UX or password handling.

## Decisions

### Decision 1: Frontend Payload Parameter Casing Alignment
- **Choice**: In `Settings.tsx`, pass `firstName: newUserFirst, lastName: newUserLast, first_name: newUserFirst, last_name: newUserLast`.
- **Rationale**: Tauri v2 `CommandItem::deserialize_json` expects `firstName` and `lastName` based on Rust parameter names. Passing both camelCase and snake_case ensures that default Tauri command deserialization succeeds immediately while safeguarding against any variant expectations.
- **Alternatives considered**: Adding `#[tauri::command(rename_all = "snake_case")]` in `lib.rs`. While valid, all other commands across the Tauri client (`api_change_password`, `set_sync_folder_path`, etc.) follow the standard Tauri camelCase convention. Aligning the frontend invocation maintains consistency across the entire client IPC layer.

## Risks / Trade-offs

- None identified. Passing additional keys in the JSON payload is safely ignored by Tauri's IPC deserializer.
