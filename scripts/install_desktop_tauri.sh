#!/usr/bin/env bash
# Install Brandy Box (Tauri client) desktop entries for current user.
# Requires a built Tauri app (AppImage) in client-tauri/src-tauri/target/release/bundle/.
# Usage: ./scripts/install_desktop_tauri.sh
#    or: REPO_ROOT=/path/to/brandyBox ./scripts/install_desktop_tauri.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
BUNDLE_DIR="$REPO_ROOT/client-tauri/src-tauri/target/release/bundle"

# Find AppImage (e.g. appimage/Brandy Box-0.2.2-x86_64.AppImage or similar)
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

if [ -z "$APPIMAGE" ] || [ ! -x "$APPIMAGE" ]; then
  echo "AppImage not found. Build the Tauri client first:"
  echo "  cd $REPO_ROOT/client-tauri"
  echo "  npm install"
  echo "  npm run tauri:build"
  exit 1
fi

# Copy to user-local location for a stable path (AppImage name includes version)
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/brandybox"
mkdir -p "$INSTALL_DIR"
cp -f "$APPIMAGE" "$INSTALL_DIR/brandybox.AppImage"
chmod +x "$INSTALL_DIR/brandybox.AppImage"
EXEC_PATH="$INSTALL_DIR/brandybox.AppImage"

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
Exec=sh -c 'pkill -f "brandybox.AppImage" 2>/dev/null || true'
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
