#!/usr/bin/env bash
# Install system dependencies for Brandy Box Tauri client (Arch/Garuda).
# Run from repo root. Requires sudo for pacman.
# Usage: ./scripts/install_tauri_prereqs.sh

set -e
if command -v pacman >/dev/null 2>&1; then
  echo "Installing Brandy Box Tauri prerequisites (webkit2gtk, gtk3, libappindicator-gtk3)..."
  sudo pacman -S --needed --noconfirm webkit2gtk gtk3 libappindicator-gtk3
  echo "Prerequisites installed."
else
  echo "Not an Arch-based system (pacman not found)."
  echo "On other distros, install: webkit2gtk, gtk3, and libappindicator3 (or equivalent)."
  exit 1
fi
