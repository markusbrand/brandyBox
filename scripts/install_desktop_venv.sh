#!/usr/bin/env bash
# Install Brandy Box desktop entries for current user (venv-based install, no PyInstaller).
# Run from repo root with venv activated, or pass REPO_ROOT and VENV_PYTHON.
# Replaces any existing entries (e.g. from a previous PyInstaller install) so the menu
# launches this venv version.
# Usage: ./scripts/install_desktop_venv.sh
#    or: REPO_ROOT=/path/to/brandyBox VENV_PYTHON=/path/to/python ./scripts/install_desktop_venv.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
VENV_PYTHON="${VENV_PYTHON:-$REPO_ROOT/.venv/bin/python}"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Venv Python not found: $VENV_PYTHON"
  echo "Activate the venv and run from repo root, or set VENV_PYTHON=..."
  exit 1
fi

APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$APPS"

# Remove old desktop entries that point to the PyInstaller build (so the menu doesn't
# show two "Brandy Box" or launch the old build)
OLD_INSTALL="$HOME/.local/share/brandybox/BrandyBox"
for f in "$APPS"/brandybox*.desktop "$APPS"/BrandyBox*.desktop; do
  [ -f "$f" ] || continue
  if grep -q "Exec=.*$OLD_INSTALL\|Exec=$OLD_INSTALL" "$f" 2>/dev/null; then
    echo "Removing old entry: $f"
    rm -f "$f"
  fi
done

ICON_LINE=""
[ -f "$REPO_ROOT/assets/logo/icon_synced.png" ] && ICON_LINE="Icon=$REPO_ROOT/assets/logo/icon_synced.png"

# Escape for desktop Exec: paths with spaces must be quoted in Exec
_exec_escape() { printf '%s' "$1" | sed "s/ /\\\\ /g"; }
PY_ESC="$(_exec_escape "$VENV_PYTHON")"

cat > "$APPS/brandybox.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Brandy Box
Comment=Sync folder to Raspberry Pi
Exec=$PY_ESC -m brandybox.main
Path=$REPO_ROOT
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
Path=$REPO_ROOT
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

# Refresh menu (KDE/GNOME pick up changes; update-desktop-database on some systems)
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q "$APPS" 2>/dev/null || true
fi

echo "Desktop entries installed to $APPS"
echo "  - Brandy Box      → $VENV_PYTHON -m brandybox.main"
echo "  - Brandy Box Settings"
echo "  - Quit Brandy Box"
echo ""
echo "If the menu still shows an old version: log out and back in, or run:"
echo "  kbuildsycoca5 --noincremental   (KDE Plasma)"
echo ""
echo "To start at login: open Brandy Box, then Settings → enable 'Start when I log in'."
