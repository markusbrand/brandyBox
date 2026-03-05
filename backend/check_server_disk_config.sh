#!/bin/bash
# Run on the Pi to verify the backend container has the right config for "Server disk (Pi)" in Settings.
# Usage: ./check_server_disk_config.sh

set -e
echo "=== Brandy Box backend – Server-Disk-Konfiguration ==="
echo ""
echo "1. Compose-Umgebung (relevant für Server-Disk):"
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml 2>/dev/null config 2>/dev/null | grep -E "BRANDYBOX_SERVER_DISK_PATH|BRANDYBOX_STORAGE_BASE_PATH|/mnt/shared_storage" || true
echo ""
echo "2. Laufende Container-Env (brandybox-backend):"
docker exec brandybox-backend env 2>/dev/null | grep -E "BRANDYBOX_SERVER_DISK_PATH|BRANDYBOX_STORAGE" || true
echo ""
echo "3. Mounts im Container:"
docker exec brandybox-backend sh -c 'echo "df /mnt/shared_storage:"; df -h /mnt/shared_storage 2>/dev/null || echo "Pfad nicht vorhanden oder nicht gemountet"' 2>/dev/null || true
echo ""
echo "Erwartung für volle HDD-Anzeige (z.B. 376 GB):"
echo "  - BRANDYBOX_SERVER_DISK_PATH=/mnt/shared_storage"
echo "  - Volume: /mnt/shared_storage:/mnt/shared_storage"
echo ""
echo "Falls Werte fehlen: Im Repo 'git pull', dann 'cd backend && ./update_brandybox.sh'"
