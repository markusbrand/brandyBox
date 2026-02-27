#!/usr/bin/env bash
# Install Brandy Box (Tauri client) desktop entries for current user.
# Requires a built Tauri app: AppImage or .deb in client-tauri/src-tauri/target/release/bundle/,
# or a release binary at target/release/brandybox.
# Usage: ./scripts/install_desktop_tauri.sh
#    or: REPO_ROOT=/path/to/brandyBox ./scripts/install_desktop_tauri.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
BUNDLE_DIR="$REPO_ROOT/client-tauri/src-tauri/target/release/bundle"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/brandybox"
EXEC_PATH=""

# 1. Try AppImage first
APPIMAGE=""
for dir in appimage ""; do
  [ -n "$dir" ] && subdir="$BUNDLE_DIR/$dir" || subdir="$BUNDLE_DIR"
  [ -d "$subdir" ] || continue
  found=$(find "$subdir" -maxdepth 1 -name "*.AppImage" -type f 2>/dev/null | head -1)
  if [ -n "$found" ] && [ -f "$found" ]; then
    APPIMAGE="$found"
    break
  fi
done

if [ -n "$APPIMAGE" ] && [ -x "$APPIMAGE" ]; then
  mkdir -p "$INSTALL_DIR"
  cp -f "$APPIMAGE" "$INSTALL_DIR/brandybox.AppImage"
  chmod +x "$INSTALL_DIR/brandybox.AppImage"
  EXEC_PATH="$INSTALL_DIR/brandybox.AppImage"
fi

# 2. Fallback: extract from .deb (for Arch/Garuda where AppImage may fail)
if [ -z "$EXEC_PATH" ]; then
  DEB=""
  for dir in deb ""; do
    [ -n "$dir" ] && subdir="$BUNDLE_DIR/$dir" || subdir="$BUNDLE_DIR"
    [ -d "$subdir" ] || continue
    found=$(find "$subdir" -maxdepth 1 -name "*.deb" -type f 2>/dev/null | head -1)
    if [ -n "$found" ] && [ -f "$found" ]; then
      DEB="$found"
      break
    fi
  done

  if [ -n "$DEB" ] && command -v ar >/dev/null 2>&1; then
    TMP_DEB="$(mktemp -d)"
    trap "rm -rf $TMP_DEB" EXIT
    (cd "$TMP_DEB" && ar x "$DEB" && tar xf data.tar.* 2>/dev/null || tar xf data.tar 2>/dev/null)
    # Tauri deb expects full structure: usr/bin/brandybox + usr/lib/Brandy Box/ (icons)
    # Extract preserving structure so resolveResource finds tray icons
    BINARY=""
    for name in "brandy-box" "brandybox" "Brandy Box"; do
      if [ -f "$TMP_DEB/usr/bin/$name" ]; then
        BINARY="$TMP_DEB/usr/bin/$name"
        break
      fi
    done
    [ -z "$BINARY" ] && BINARY=$(find "$TMP_DEB/usr/bin" -type f 2>/dev/null | head -1)
    if [ -n "$BINARY" ] && [ -x "$BINARY" ]; then
      rm -rf "$INSTALL_DIR"
      mkdir -p "$INSTALL_DIR"
      cp -a "$TMP_DEB/usr" "$INSTALL_DIR/"
      EXEC_PATH="$INSTALL_DIR/usr/bin/$(basename "$BINARY")"
    fi
  fi
fi

# 3. Fallback: use release binary (from cargo build --release)
if [ -z "$EXEC_PATH" ]; then
  RELEASE_BIN="$REPO_ROOT/client-tauri/src-tauri/target/release/brandybox"
  if [ -x "$RELEASE_BIN" ]; then
    mkdir -p "$INSTALL_DIR"
    cp -f "$RELEASE_BIN" "$INSTALL_DIR/brandybox"
    chmod +x "$INSTALL_DIR/brandybox"
    EXEC_PATH="$INSTALL_DIR/brandybox"
  fi
fi

if [ -z "$EXEC_PATH" ]; then
  echo "No built Tauri app found. Build first:"
  echo "  cd $REPO_ROOT/client-tauri"
  echo "  npm install"
  echo "  npm run tauri:build"
  echo ""
  echo "Note: AppImage may fail on some systems; the .deb is used as fallback on Arch/Garuda."
  exit 1
fi

APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$APPS"

# Icon from Tauri bundle or repo
ICON_LINE=""
for p in "$REPO_ROOT/client-tauri/src-tauri/icons/128x128.png" "$REPO_ROOT/assets/logo/icon_synced.png"; do
  [ -f "$p" ] && ICON_LINE="Icon=$p" && break
done

# Escape for desktop Exec
_exec_escape() { printf '%s' "$1" | sed "s/ /\\\\ /g"; }
EXEC_ESC="$(_exec_escape "$EXEC_PATH")"

# For pkill: match the actual executable name
PKILL_PATTERN="brandybox.AppImage"
[[ "$EXEC_PATH" == *"brandybox"* ]] && [[ "$EXEC_PATH" != *".AppImage"* ]] && PKILL_PATTERN="brandybox"

cat > "$APPS/brandybox.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Brandy Box
Comment=Sync folder to Raspberry Pi
Exec=$EXEC_ESC
$ICON_LINE
Categories=Utility;
StartupNotify=false
EOF

cat > "$APPS/brandybox-settings.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Brandy Box Settings
Comment=Configure sync folder and options
Exec=$EXEC_ESC
$ICON_LINE
Categories=Utility;Settings;
StartupNotify=false
EOF

cat > "$APPS/brandybox-quit.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Quit Brandy Box
Comment=Stop the Brandy Box tray app
Exec=sh -c 'pkill -f "$PKILL_PATTERN" 2>/dev/null || true'
$ICON_LINE
Categories=Utility;
StartupNotify=false
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q "$APPS" 2>/dev/null || true
fi

echo "Desktop entries installed to $APPS"
echo "  - Brandy Box        → $EXEC_PATH"
echo "  - Brandy Box Settings (opens main window)"
echo "  - Quit Brandy Box"
echo ""
echo "If the menu still shows an old version: kbuildsycoca5 --noincremental (KDE)"
echo ""
echo "To start at login: open Brandy Box, then Settings → enable 'Start when I log in'."
