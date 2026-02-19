# install-brandybox-server

How to **update the Brandy Box backend** on the Raspberry Pi. The image is **built and published by GitHub Actions** to GitHub Container Registry (GHCR); on the Pi you pull the new image and restart the container. SSH from your Garuda PC to the Pi at **192.168.0.150** (public key, no password).

---

## How updates work

- **GitHub Actions** (workflow `publish-backend-image.yml`) builds and pushes the backend image to `ghcr.io/markusbrand/brandybox-backend:latest` on:
  - push to `master` or `main` (when `backend/**` or the workflow file changes),
  - release publish,
  - or manual **workflow_dispatch** in the GitHub Actions tab.
- **On the Pi** you use that image via `docker-compose.ghcr.yml`. Updating the server = pull latest image and restart (no local build, no git pull of source on the Pi).

---

## 1. SSH into the Raspberry Pi

From your Garuda PC:

```bash
ssh pi
```

- Replace `pi` with your Pi username if different.
- If you use a specific key: `ssh -i ~/.ssh/your_key pi@192.168.0.150`.

---

## 2. Pull the new image and restart the backend

On the Pi. Repo path is assumed `~/brandyBox`; change it if your clone is elsewhere.

```bash
cd ~/brandyBox/backend
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
```

- `pull` fetches the latest image from GHCR (built by the last successful GitHub Actions run).
- `up -d` recreates the container with the new image. Your existing `.env` and volumes are unchanged.

If the package is **private**, log in once (or when token expires):  
`docker login ghcr.io` (username: GitHub user, password: PAT with `read:packages`).

---

## 3. Check that the backend is up

Wait a few seconds for the app to start, then:

```bash
sleep 15
curl -s http://localhost:8081/health
```

- Expected: `{"status":"ok"}` (or similar). Use the port from your `.env` (e.g. 8082) if different.

Optional: container status and logs:

```bash
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml ps
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml logs --tail 50
```

---

## 4. Exit SSH

```bash
exit
```

---

## One-liner (from Garuda PC)

Update the server in one SSH session:

```bash
ssh pi 'cd ~/brandyBox/backend && docker compose -f docker-compose.yml -f docker-compose.ghcr.yml pull && docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d'
```

Then check health from your PC:

```bash
sleep 15
curl -s http://192.168.0.150:8081/health
```

---

## Optional: automatic updates (webhook + cron)

When GitHub Actions has built the new image, the Pi can update itself without manual SSH:

- **Webhook listener** (`backend/webhook_listener.py`): Flask app on port 9000. Configure a GitHub webhook (repo → Settings → Webhooks) to call your Pi (e.g. via Cloudflare tunnel) at `/webhook`. Set `GITHUB_WEBHOOK_SECRET` in the environment to match the webhook secret. On successful `workflow_run` completion, the listener runs `backend/update_brandybox.sh`, which pulls the latest image and restarts the container.
- **Cron:** Use a cron job (e.g. `@reboot`) to start the webhook listener after a reboot, or run `update_brandybox.sh` periodically (e.g. daily) as a fallback.

See the main [README](../../README.md) (backend section 7) and [Backend overview](../../docs/backend/overview.md) for details.

---

## First-time setup on the Pi (GHCR)

If the backend is not yet running from GHCR:

1. On the Pi: clone the repo (or copy `backend/` with `docker-compose.yml`, `docker-compose.ghcr.yml`, and create `.env` from `.env.example`).
2. Ensure storage path exists and is writable (e.g. `/mnt/shared_storage/brandyBox`).
3. Run:  
   `cd ~/brandyBox/backend`  
   `docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d`  
   (and configure `.env` before that if needed).

See the main [README](../../README.md) backend section for `.env` and storage.

---

## Optional: build and run locally on the Pi (no GHCR)

If you prefer to build the image on the Pi instead of using GHCR:

```bash
cd ~/brandyBox
git fetch origin && git pull origin master   # or main
cd backend
docker compose build --no-cache
docker compose up -d
```

- Use this only when you need a local build (e.g. no GHCR access or testing uncommitted changes). Do **not** overwrite `backend/.env` when pulling.

---

## Summary

| Step | Where | Command |
|------|--------|---------|
| **Trigger image build** | GitHub | Push to `master`/`main` (backend changes) or run workflow manually |
| **Update server** | On Pi (or via SSH) | `cd ~/brandyBox/backend` → `docker compose -f docker-compose.yml -f docker-compose.ghcr.yml pull` → `… up -d` |
| **Verify** | On Pi or from PC | `curl -s http://localhost:8081/health` or `http://192.168.0.150:8081/health` |

- Image: `ghcr.io/markusbrand/brandybox-backend:latest`.
- Keep `backend/.env` (JWT secret, SMTP, admin) safe; it is not in the image.

This command is available in chat as `/install-brandybox-server`.
