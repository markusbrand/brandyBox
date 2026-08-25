#!/usr/bin/env bash
# Run the installed Brandy Box (Tauri) if available.
# Use this instead of tauri dev on Wayland: dev mode doesn't show the tray icon,
# but the installed release build does.
# Usage: ./scripts/run_brandybox_installed.sh
# Exit 0 if started, 1 if not installed.

set -e
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/brandybox"

if [ -x "$INSTALL_DIR/usr/bin/brandybox" ]; then
  exec "$INSTALL_DIR/usr/bin/brandybox" "$@"
elif [ -x "$INSTALL_DIR/brandybox.AppImage" ]; then
  exec "$INSTALL_DIR/brandybox.AppImage" "$@"
else
  echo "Brandy Box not installed. Run: ./scripts/install_desktop_tauri.sh (after building)"
  exit 1
fi
