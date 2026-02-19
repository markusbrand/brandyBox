#!/bin/bash
# Pull latest Brandy Box backend image from GHCR and restart the container.
# Used by the GitHub webhook listener when a workflow run completes successfully.
# Run from anywhere; uses repo path relative to this script.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR"
cd "$BACKEND_DIR"

echo "Pulling latest image and restarting backend..."
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
echo "Backend updated."
