# Releasing Brandy Box

This page describes how to create a new GitHub release. Releases trigger:

- **Build Client for Release**: Builds the Tauri client for Windows (NSIS), Linux (deb, rpm, AppImage), and macOS (Arm + Intel) and attaches artifacts to the release. Linux assets: **.deb** (Debian/Ubuntu), **.rpm** (Red Hat/Fedora/openSUSE), **.AppImage** (portable, e.g. Arch Linux).
- **Publish Backend to GHCR**: Builds and pushes the backend Docker image to `ghcr.io/markusbrand/brandybox-backend` with the release tag.

## How the client build works

The **Build Client for Release** workflow runs on **GitHub Actions**. Each platform (Windows, Linux, macOS Arm, macOS Intel) is built on GitHub’s own runner for that OS. **It does not matter whether you trigger the workflow from a Linux PC, Windows PC, or Mac**—all four jobs run on GitHub’s infrastructure. Trigger the workflow from the repo (e.g. Actions → Build Client for Release → Run workflow) and wait for all jobs to finish; the artifacts are then attached to the release.

Do not rely on building the client for all platforms on your local machine; use the GitHub workflow for releases.

### Linux package formats

Each release includes three Linux artifacts:

| Format     | File        | Use on |
|-----------|-------------|--------|
| Debian    | `*.deb`     | Debian, Ubuntu |
| RPM       | `*.rpm`     | Red Hat, Fedora, openSUSE, SUSE |
| AppImage  | `*.AppImage`| Portable (e.g. Arch Linux); no system package manager needed |

## Prerequisites

- Clean working tree (`git status` clean).
- Version numbers updated in code (see version locations below) if this is a new version.
- Push access to the GitHub repo.

## Version locations

Update these to the new version before tagging (or use `scripts/release.sh`):

| Location | Purpose |
|----------|---------|
| `client-tauri/package.json` | `version` |
| `client-tauri/src-tauri/tauri.conf.json` | `version` |
| `client/pyproject.toml` | Python client `version` (optional; can lag Tauri) |

## Option A: Create release from current HEAD (recommended)

Use this when you want to release the current state of `master` with a new version number.

1. **Bump versions** (edit files above or run the release script):
   ```bash
   ./scripts/release.sh 0.2.3
   ```
   This updates the three version fields, commits, and creates tag `v0.2.3`.

2. **Push branch and tag**:
   ```bash
   git push origin master
   git push origin v0.2.3
   ```

3. **Create the GitHub release** (this triggers the workflows):
   - Go to [Releases](https://github.com/markusbrand/brandyBox/releases) → **Draft a new release**.
   - Choose tag **v0.2.3** (create from existing tag).
   - Set title e.g. **v0.2.3** and add release notes.
   - Click **Publish release**.

4. **Wait for workflows**  
   - **Build Client for Release** will build Windows/Linux/macOS zips and attach them to the release.  
   - **Publish Backend to GHCR** will build and push the backend image with tag `0.2.3`.

## Option B: Release an existing tag

If the tag (e.g. `v0.2.2`) already exists and you only need to (re-)publish the release or re-run builds:

1. Go to [Releases](https://github.com/markusbrand/brandyBox/releases).
2. Either create a new release for that tag, or use **Actions** → **Build Client for Release** → **Run workflow** and enter the tag in `release_tag` to build and attach assets to an existing release.

## Option C: Build client assets without a release (workflow_dispatch)

To only build the client artifacts (e.g. for testing):

1. **Actions** → **Build Client for Release** → **Run workflow**.
2. Leave **release_tag** empty. Artifacts will be named with version `dev` and will not be attached to any release.

## Summary

| Step | Action |
|------|--------|
| 1 | Bump versions (script or manually), commit, tag (e.g. `v0.2.3`). |
| 2 | `git push origin master && git push origin v0.2.3` |
| 3 | GitHub → Releases → Draft new release → select tag → Publish. |
| 4 | Workflows build client assets and backend image automatically. |
