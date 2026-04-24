#!/bin/bash
# Pull latest Brandy Box backend image from GHCR and restart the container.
# Used by the GitHub webhook listener when a workflow run completes successfully.
# Run from anywhere; uses repo path relative to this script.
#
# If you added new env vars or volumes in docker-compose.yml, run "git pull" in the
# repo root first so this script uses the updated compose file.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR"
cd "$BACKEND_DIR"

echo "Pulling latest image and restarting backend..."
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml pull
# Force a new container so a changed image digest is always applied (compose can
# otherwise leave "Running" without recreating when the service spec looks unchanged).
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d --force-recreate
echo "Backend updated."
