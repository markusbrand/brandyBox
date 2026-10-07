## Context

See `proposal.md` for background and problem statement. In `client-tauri/src-tauri/src/config.rs`, `expand_tilde` expands tilde paths using `s.trim_start_matches('~').trim_start_matches('/')`. On Windows, backslashes are not trimmed. Joining `\brandyBox` with `home` causes `Path::join` to replace all path components following the drive letter with `\brandyBox`, causing the sync directory to resolve to `C:\brandyBox`. In `client-tauri/src-tauri/src/sync.rs`, `safe_local_path` replaces `/` with `MAIN_SEPARATOR_STR`, which leaves backslashes untouched on Unix platforms.

## Goals / Non-Goals

**Goals:**
- Correctly strip both `/` and `\` from `~` path prefixes in `expand_tilde` and return `home` if the rest of the string is empty or contains only separators.
- Ensure `safe_local_path` converts path components separated by `/` or `\` into native path components by splitting and pushing non-empty segments onto the local root.
- Validate the behavior with comprehensive unit tests for both functions.

**Non-Goals:**
- Modifying how backend storage paths are resolved or stored (already covered by backend canonicalization specifications).
- Altering the desktop client's sync state serialization format.

## Decisions

### Decision 1: Character Predicate for Trimming in `expand_tilde`
- **Choice**: Use `.trim_start_matches(|c| c == '/' || c == '\\')` after trimming `~`.
- **Rationale**: This strips both Unix-style forward slashes and Windows-style backslashes regardless of the OS where the configuration was authored or edited. If `rest.is_empty()`, return `home` directly to prevent joining an empty slice or root separator.
- **Alternatives considered**: Only conditionally trimming `\` on `#[cfg(windows)]`. Rejected because users can sync or copy configuration files between operating systems or provide forward/backward slashes interchangeably.

### Decision 2: Segment-by-Segment Construction in `safe_local_path`
- **Choice**: Iterate over segments using `.split(['/', '\\'])`, validate each segment (rejecting `..` and skipping `.`), and build the final `PathBuf` by pushing valid segments with `local.push(segment)`.
- **Rationale**: `PathBuf::push` natively formats directory separators for the active target platform, eliminating string replacement flaws when paths contain foreign separators.
- **Alternatives considered**: `trimmed.replace('\\', "/").replace('/', MAIN_SEPARATOR_STR)`. Pushing segments is cleaner, safer, and already required for directory traversal validation.

## Risks / Trade-offs

- [Risk] A valid filename containing a backslash on Unix could be interpreted as a directory separator.
  → Mitigation: In cross-platform sync systems, backslash characters in filenames are illegal on Windows anyway; interpreting backslash as a path separator ensures cross-platform consistency.
