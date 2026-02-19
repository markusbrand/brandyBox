#!/bin/bash
# Pfad: /home/pi/brandyBox/backend/update_brandybox.sh

echo "Starte Update für brandyBox Backend..."

# Ins Backend-Verzeichnis wechseln
cd /home/pi/brandyBox/backend

# Neuestes Image von GitHub Packages ziehen
docker pull ghcr.io/markusbrand/brandybox:latest

# Container neu starten
docker stop brandybox || true
docker rm brandybox || true

# Wir mappen:
# 1. Den Port 8081
# 2. Den Shared Storage für die Benutzerdaten (HDD)
# 3. Den lokalen Backend-Ordner für die DB/Configs (SSD)
docker run -d \
  --name brandybox \
  -p 8081:8081 \
  -v /mnt/shared_storage/brandyBox:/data \
  -v /home/pi/brandyBox/backend:/app/config \
  --restart unless-stopped \
  ghcr.io/markusbrand/brandybox:latest

echo "Backend erfolgreich aktualisiert."
