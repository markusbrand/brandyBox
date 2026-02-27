# release-client-github

Build a new Brandy Box **Tauri client** release on GitHub: bump version, tag, push, and create a published release so the **Build Client for Release** workflow builds and attaches Windows, Linux, and macOS zips.

**Version bump (by user request):**
- **Default:** Bump to the next **patch** (bugfix) version (e.g. `0.2.1` → `0.2.2`).
- **If the user says "minor", "minor version", or "minor release":** Bump to the next **minor** version (e.g. `0.2.1` → `0.3.0`).
- **If the user says "major", "major version", or similar:** Bump to the next **major** version (e.g. `0.2.0` → `1.0.0`).

---

## Agent behavior (execute autonomously)

When the user invokes this command:

1. **Determine bump type:** If the user’s message indicates a **major** release (e.g. "major", "major version", "bump major"), plan to bump the **major** version (x.y.z → (x+1).0.0). If the user says **minor**, **minor version**, or **minor release**, plan to bump the **minor** version (x.y.z → x.(y+1).0). Otherwise (default) use the next **patch** (bugfix) version (x.y.z → x.y.(z+1)).
2. **Read current version** from `client-tauri/src-tauri/tauri.conf.json` (e.g. `0.2.1`).
3. **Compute new version** (patch: increment last only; minor: increment middle, set patch to 0; major: increment first, set middle and patch to 0).
4. **Update** these files with the new version (keep in sync): `client-tauri/src-tauri/tauri.conf.json` (field `version`), `client-tauri/src-tauri/Cargo.toml` (package `version`), `client-tauri/package.json` (field `version`).
5. **Commit:** `git add client-tauri/src-tauri/tauri.conf.json client-tauri/src-tauri/Cargo.toml client-tauri/package.json && git commit -m "Bump Tauri client version to <new_version>"`.
6. **Tag:** `git tag v<new_version>` (e.g. `v0.2.2`, `v0.3.0`, or `v1.0.0`).
7. **Push:** `git push origin <current_branch>` then `git push origin v<new_version>`.
8. **Create GitHub release:** `gh release create v<new_version> --title "Tauri Client <new_version>" --notes "Brandy Box Tauri desktop client <new_version>. Build artifacts (Windows, Linux, macOS) will be attached by the Build Client for Release workflow."`
9. Tell the user the release URL and that the workflow will attach the zip assets when it finishes.

Use the actual workspace path and current branch; request `git_write` and `network` where needed for commit, push, and `gh`.

---

## Summary

| Bump   | Example (from 0.2.1) |
|--------|----------------------|
| Patch / bugfix (default) | 0.2.2 |
| Minor (user says "minor", "minor version", "minor release") | 0.3.0 |
| Major (user says "major", "major version") | 1.0.0 |

This command is available in chat as `/release-client-github`. By default the next **patch** (bugfix) version is used. Say **minor** (or "minor version" / "minor release") for the next minor version, or **major** (or "major version") for the next major version.
