#!/usr/bin/env bash
# Bump version to the given semver (e.g. 0.2.3), commit, and create tag v<version>.
# Usage: ./scripts/release.sh 0.2.3
# Does not push; run: git push origin master && git push origin v0.2.3

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <version>   (e.g. 0.2.3)"
  exit 1
fi

VERSION="$1"
TAG="v${VERSION}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Validate version format (basic semver)
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$ ]]; then
  echo "Error: version should be semver (e.g. 0.2.3), got: $VERSION"
  exit 1
fi

if [[ -n $(git -C "$ROOT" status --porcelain) ]]; then
  echo "Error: working tree is not clean. Commit or stash changes first."
  exit 1
fi

if git -C "$ROOT" rev-parse "$TAG" &>/dev/null; then
  echo "Error: tag $TAG already exists."
  exit 1
fi

echo "Bumping version to $VERSION and creating tag $TAG"

# client-tauri/package.json
sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" "$ROOT/client-tauri/package.json"

# client-tauri/package-lock.json (root package version only; first occurrence)
sed -i "0,/\"version\": \"[^\"]*\"/ s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" "$ROOT/client-tauri/package-lock.json"

# client-tauri/src-tauri/tauri.conf.json
sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" "$ROOT/client-tauri/src-tauri/tauri.conf.json"

# client-tauri/src-tauri/Cargo.toml (Tauri app crate)
sed -i "s/^version = \"[^\"]*\"$/version = \"$VERSION\"/" "$ROOT/client-tauri/src-tauri/Cargo.toml"

# client/pyproject.toml (Python client; keep in sync for consistency)
sed -i "s/^version = \"[^\"]*\"$/version = \"$VERSION\"/" "$ROOT/client/pyproject.toml"

git -C "$ROOT" add client-tauri/package.json client-tauri/package-lock.json client-tauri/src-tauri/tauri.conf.json client-tauri/src-tauri/Cargo.toml client/pyproject.toml
git -C "$ROOT" commit -m "Bump version to $VERSION"
git -C "$ROOT" tag -a "$TAG" -m "Release $TAG"

echo "Done. Version bumped and tag $TAG created."
echo "Push with: git push origin master && git push origin $TAG"
echo "Then create the release on GitHub: https://github.com/markusbrand/brandyBox/releases/new?tag=$TAG"
