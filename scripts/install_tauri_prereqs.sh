#!/usr/bin/env bash
# Install system dependencies for Brandy Box Tauri client (Arch/Garuda).
# Run from repo root. Requires sudo for pacman.
# Usage: ./scripts/install_tauri_prereqs.sh
#
# Tray: Tauri prefers libayatana-appindicator on Linux. If tray still doesn't show
# on Wayland, see docs/client/troubleshooting.md (known Tauri bug: dev/deb fail on Wayland).

set -e
if command -v pacman >/dev/null 2>&1; then
  echo "Installing Brandy Box Tauri prerequisites (webkit2gtk, gtk3, libayatana-appindicator)..."
  sudo pacman -S --needed --noconfirm webkit2gtk gtk3 libayatana-appindicator
  echo "Prerequisites installed."
  echo ""
  echo "If the tray icon still does not appear on Wayland: run under X11, or use"
  echo "the AppImage build. See docs/client/troubleshooting.md for details."
else
  echo "Not an Arch-based system (pacman not found)."
  echo "On other distros, install: webkit2gtk, gtk3, and libayatana-appindicator (or libappindicator3)."
  exit 1
fi
