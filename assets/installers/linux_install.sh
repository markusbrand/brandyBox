#!/bin/bash
# Install Brandy Box for current user (no sudo). Run after building with PyInstaller.
# Usage: ./linux_install.sh [path-to-BrandyBox-folder]
# Default: repo root dist/BrandyBox (pyinstaller client/brandybox.spec output).

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIST="${1:-$REPO_ROOT/dist/BrandyBox}"
INSTALL_DIR="$HOME/.local/share/brandybox"
APPS="$HOME/.local/share/applications"
AUTOSTART="$HOME/.config/autostart"

if [ ! -f "$DIST/BrandyBox" ]; then
  echo "Build folder not found: $DIST (run: pyinstaller client/brandybox.spec from repo root)"
  exit 1
fi

mkdir -p "$INSTALL_DIR"
cp -R "$DIST"/* "$INSTALL_DIR/"
EXEC="$INSTALL_DIR/BrandyBox"
chmod +x "$EXEC"

mkdir -p "$APPS"
cat > "$APPS/brandybox.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Brandy Box
Comment=Sync folder to Raspberry Pi
Exec=$EXEC
Icon=brandybox
Categories=Utility;
StartupNotify=false
EOF

mkdir -p "$AUTOSTART"
# Optional: copy to autostart if user has enabled it in settings
# cp "$APPS/brandybox.desktop" "$AUTOSTART/" 

echo "Installed to $INSTALL_DIR"
echo "Run: $EXEC"
echo "Desktop entry: $APPS/brandybox.desktop"
