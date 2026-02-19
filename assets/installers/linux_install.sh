#!/bin/bash
# Install Brandy Box for current user (no sudo).
# Usage:
#   ./linux_install.sh [path-to-BrandyBox-folder]   # PyInstaller build (standalone binary)
#   ./linux_install.sh --venv                       # Use repo .venv (recommended on Linux for proper tray icon + menu)
# Default path: repo root dist/BrandyBox (pyinstaller client/brandybox.spec output).

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
APPS="$HOME/.local/share/applications"
AUTOSTART="$HOME/.config/autostart"

USE_VENV=false
if [ "${1:-}" = "--venv" ]; then
  USE_VENV=true
  shift
fi

if [ "$USE_VENV" = true ]; then
  VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
  if [ ! -x "$VENV_PYTHON" ]; then
    echo "Venv not found: $VENV_PYTHON"
    echo "Create it from repo root: python -m venv .venv && source .venv/bin/activate && cd client && pip install -e . && cd .."
    exit 1
  fi
  INSTALL_DIR="$HOME/.local/share/brandybox"
  mkdir -p "$APPS"
  # Escape spaces in paths for Desktop Exec
  _e() { printf '%s' "$1" | sed 's/ /\\ /g'; }
  PY_ESC="$(_e "$VENV_PYTHON")"
  ROOT_ESC="$(_e "$REPO_ROOT")"
  ICON_LINE=""
  [ -f "$REPO_ROOT/assets/logo/icon_synced.png" ] && ICON_LINE="Icon=$REPO_ROOT/assets/logo/icon_synced.png"

  cat > "$APPS/brandybox.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Brandy Box
Comment=Sync folder to Raspberry Pi
Exec=$PY_ESC -m brandybox.main
Path=$ROOT_ESC
$ICON_LINE
Categories=Utility;
StartupNotify=false
EOF

  cat > "$APPS/brandybox-settings.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Brandy Box Settings
Comment=Configure sync folder and options
Exec=$PY_ESC -m brandybox.main --settings
Path=$ROOT_ESC
$ICON_LINE
Categories=Utility;Settings;
StartupNotify=false
EOF

  cat > "$APPS/brandybox-quit.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Quit Brandy Box
Comment=Stop the Brandy Box tray app
Exec=sh -c 'pkill -f "brandybox.main" 2>/dev/null || true'
$ICON_LINE
Categories=Utility;
StartupNotify=false
EOF

  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q "$APPS" 2>/dev/null || true
  fi

  echo "Installed desktop entries (venv): $APPS"
  echo "  Brandy Box, Brandy Box Settings, Quit Brandy Box"
  echo "  Uses: $VENV_PYTHON -m brandybox.main  (proper tray icon + context menu on Garuda/KDE)"
  echo ""
  echo "If the menu still shows an old icon, run: kbuildsycoca5 --noincremental  (KDE)"
  exit 0
fi

# --- PyInstaller build install ---
DIST="${1:-$REPO_ROOT/dist/BrandyBox}"
INSTALL_DIR="$HOME/.local/share/brandybox"

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

cat > "$APPS/brandybox-settings.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Brandy Box Settings
Comment=Configure sync folder and options
Exec=$EXEC --settings
Icon=brandybox
Categories=Utility;Settings;
StartupNotify=false
EOF

cat > "$APPS/brandybox-quit.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Quit Brandy Box
Comment=Stop the Brandy Box tray app (use when the tray menu does not open)
Exec=killall BrandyBox 2>/dev/null || true
Icon=brandybox
Categories=Utility;
StartupNotify=false
EOF

mkdir -p "$AUTOSTART"

echo "Installed to $INSTALL_DIR"
echo "Run: $EXEC  (or 'Brandy Box Settings' to open Settings only)"
echo "Desktop entries: $APPS/brandybox.desktop, $APPS/brandybox-settings.desktop, $APPS/brandybox-quit.desktop"
echo ""
echo "On Linux (Garuda/KDE) the standalone binary may show a square tray icon and no context menu."
echo "For the proper tray icon and menu, use the venv install from repo root:"
echo "  ./assets/installers/linux_install.sh --venv"
