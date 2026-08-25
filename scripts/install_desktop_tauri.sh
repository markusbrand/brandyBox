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
    # Use newest .deb by mtime so we install the latest build (e.g. 0.2.3 over 0.2.2)
    found=$(ls -t "$subdir"/*.deb 2>/dev/null | head -1)
    [ -z "$found" ] && found=$(find "$subdir" -maxdepth 1 -name "*.deb" -type f 2>/dev/null | head -1)
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

# Always prefer the latest release binary if it is newer (avoids stale client after code changes)
RELEASE_BIN="$REPO_ROOT/client-tauri/src-tauri/target/release/brandybox"
if [ -x "$RELEASE_BIN" ] && [ -f "$EXEC_PATH" ] && [ "$RELEASE_BIN" -nt "$EXEC_PATH" ]; then
  cp -f "$RELEASE_BIN" "$EXEC_PATH"
  chmod +x "$EXEC_PATH"
fi

APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$APPS"

# Remove old/separate clutter desktop entries
rm -f "$APPS/brandybox-settings.desktop" "$APPS/brandybox-quit.desktop"

# Install standard XDG hicolor icons across resolutions (SVG + PNG)
ICONS_BASE="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
ICON_SRC_DIR="$REPO_ROOT/client-tauri/src-tauri/icons"

mkdir -p "$ICONS_BASE/scalable/apps" "$ICONS_BASE/512x512/apps" "$ICONS_BASE/256x256/apps" "$ICONS_BASE/128x128/apps" "$ICONS_BASE/64x64/apps" "$ICONS_BASE/48x48/apps" "$ICONS_BASE/32x32/apps" "$ICONS_BASE/16x16/apps" "${XDG_DATA_HOME:-$HOME/.local/share}/pixmaps"

# Scalable vector icon (critical for Garuda / BeautyLine / Sweet themes)
[ -f "$ICON_SRC_DIR/brandybox.svg" ] && cp -f "$ICON_SRC_DIR/brandybox.svg" "$ICONS_BASE/scalable/apps/brandybox.svg"
[ -f "$ICON_SRC_DIR/brandybox.svg" ] && cp -f "$ICON_SRC_DIR/brandybox.svg" "${XDG_DATA_HOME:-$HOME/.local/share}/pixmaps/brandybox.svg"

# Also install into user icon themes if present (e.g. BeautyLine, Sweet)
for theme in BeautyLine Sweet Candy Papirus Tela; do
  THEME_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/$theme/apps/scalable"
  mkdir -p "$THEME_DIR"
  [ -f "$ICON_SRC_DIR/brandybox.svg" ] && cp -f "$ICON_SRC_DIR/brandybox.svg" "$THEME_DIR/brandybox.svg"
done

# PNG fallbacks
[ -f "$ICON_SRC_DIR/icon.png" ] && cp -f "$ICON_SRC_DIR/icon.png" "$ICONS_BASE/512x512/apps/brandybox.png"
[ -f "$ICON_SRC_DIR/128x128@2x.png" ] && cp -f "$ICON_SRC_DIR/128x128@2x.png" "$ICONS_BASE/256x256/apps/brandybox.png"
[ -f "$ICON_SRC_DIR/128x128.png" ] && cp -f "$ICON_SRC_DIR/128x128.png" "$ICONS_BASE/128x128/apps/brandybox.png"
[ -f "$ICON_SRC_DIR/icon_synced.png" ] && cp -f "$ICON_SRC_DIR/icon_synced.png" "$ICONS_BASE/64x64/apps/brandybox.png"
[ -f "$ICON_SRC_DIR/32x32.png" ] && cp -f "$ICON_SRC_DIR/32x32.png" "$ICONS_BASE/32x32/apps/brandybox.png"
[ -f "$ICON_SRC_DIR/icon.png" ] && cp -f "$ICON_SRC_DIR/icon.png" "${XDG_DATA_HOME:-$HOME/.local/share}/pixmaps/brandybox.png"

# Also copy icons into INSTALL_DIR for bundle runtime
mkdir -p "$INSTALL_DIR/icons"
cp -rf "$ICON_SRC_DIR"/* "$INSTALL_DIR/icons/" 2>/dev/null || true

# Escape for desktop Exec
_exec_escape() { printf '%s' "$1" | sed "s/ /\\\\ /g"; }
EXEC_ESC="$(_exec_escape "$EXEC_PATH")"

# For pkill: match the actual executable name
PKILL_PATTERN="brandybox.AppImage"
[[ "$EXEC_PATH" == *"brandybox"* ]] && [[ "$EXEC_PATH" != *".AppImage"* ]] && PKILL_PATTERN="brandybox"

# Create single Brandy Box desktop entry with right-click actions
cat > "$APPS/brandybox.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Brandy Box
Comment=Sync folder to Raspberry Pi
Exec=env GDK_BACKEND=x11 $EXEC_ESC
Icon=brandybox
Categories=Utility;Network;FileTransfer;
StartupNotify=false
StartupWMClass=brandybox
Actions=Settings;Quit;

[Desktop Action Settings]
Name=Open Settings
Exec=env GDK_BACKEND=x11 $EXEC_ESC

[Desktop Action Quit]
Name=Quit Brandy Box
Exec=sh -c 'pkill -f "$PKILL_PATTERN" 2>/dev/null || true'
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q "$APPS" 2>/dev/null || true
fi

[ ! -f "$ICONS_BASE/index.theme" ] && [ -f /usr/share/icons/hicolor/index.theme ] && cp /usr/share/icons/hicolor/index.theme "$ICONS_BASE/index.theme" || true

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$ICONS_BASE" 2>/dev/null || true
fi

# Clear KDE Plasma stale icon caches
rm -f "$HOME/.cache/icon-cache.kcache" "$HOME/.cache"/plasma_theme_*.kcache "$HOME/.cache"/ksycoca* "$HOME/.cache"/plasma-svgelements* 2>/dev/null || true

if command -v kbuildsycoca6 >/dev/null 2>&1; then
  kbuildsycoca6 --noincremental 2>/dev/null || true
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
  kbuildsycoca5 --noincremental 2>/dev/null || true
fi

echo "Desktop entry installed to $APPS/brandybox.desktop"
echo "  - Application: Brandy Box"
echo "  - Exec:        $EXEC_PATH"
echo "  - Icon:        brandybox (SVG + PNG installed to $ICONS_BASE)"
echo ""
echo "To start at login: open Brandy Box, then Settings → enable 'Start when I log in'."

