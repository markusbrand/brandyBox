# Raspberry Pi Installation and Update Guide

Brandy Box is designed to run on a Raspberry Pi (ideally Raspberry Pi 5) using Docker.

## Prerequisites

1.  **Docker Installed**:
    ```bash
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    # Log out and back in for group changes to take effect
    ```
2.  **Storage Directory**: Ensure your storage mount exists and is writable.
    ```bash
    sudo mkdir -p /mnt/shared_storage/brandyBox
    sudo chown $USER:$USER /mnt/shared_storage/brandyBox
    ```

## Installation (Fastest Method)

You can run the backend without cloning the repository by using the pre-built Docker image from GitHub Container Registry (GHCR).

1.  **Prepare configuration**:
    ```bash
    mkdir -p ~/brandybox && cd ~/brandybox
    curl -sL https://raw.githubusercontent.com/markusbrand/brandyBox/master/backend/.env.example -o .env
    # Edit .env and set at least BRANDYBOX_JWT_SECRET, BRANDYBOX_ADMIN_EMAIL, and BRANDYBOX_ADMIN_INITIAL_PASSWORD
    ```
2.  **Run with Docker**:
    ```bash
    docker run -d \
      --name brandybox-backend \
      --restart unless-stopped \
      -p 8081:8080 \
      -v brandybox_data:/data \
      -v /mnt/shared_storage/brandyBox:/mnt/shared_storage/brandyBox \
      --env-file .env \
      ghcr.io/markusbrand/brandybox-backend:latest
    ```

## Updating Brandy Box

### Manual Update
If you installed using the `docker run` command above:
```bash
docker pull ghcr.io/markusbrand/brandybox-backend:latest
docker stop brandybox-backend
docker rm brandybox-backend
# Re-run the docker run command from above
```

### Update via Docker Compose (Recommended for Development)
If you cloned the repository:
```bash
cd ~/brandyBox
git pull
cd backend
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d --force-recreate
```

### Automatic Updates (Webhook)
Brandy Box includes a webhook listener that can automatically update the backend when a new image is published.
1. Run `backend/webhook_listener.py` on your Pi.
2. Configure a GitHub webhook to point to your Pi's listener.
3. When the `publish-backend-image.yml` workflow succeeds, your Pi will automatically pull and restart.

## Accessing Brandy Box
- **Web UI**: Visit `http://<pi-ip>:8081` in your browser.
- **Desktop Client**: Install the Tauri client on your computer and point it to your Pi's IP or Cloudflare tunnel URL.
