# install-brandybox-server

How to **trigger a Brandy Box backend update**: the image is built and published by GitHub Actions to GHCR; the **Raspberry Pi updates automatically** via the webhook listener—no manual SSH needed. This command covers triggering the build and **verifying in webhook.log** that the Pi actually applied the update.

**Second option:** If you want a **direct update** (build and run from code on the Pi, **without GitHub** / **without GHCR**), e.g. for **build from source** or **test build**, use **Option 2** below (SSH → pull code → build image on Pi → restart).

---

## How it works (Option 1 — GHCR + webhook)

- **GitHub Actions** (workflow `publish-backend-image.yml`) builds and pushes the backend image to `ghcr.io/markusbrand/brandybox-backend:latest` on:
  - push to `master` or `main` (when `backend/**` or the workflow file changes),
  - release publish,
  - or manual **workflow_dispatch** in the GitHub Actions tab.
- **On the Pi**, `webhook_listener.py` (port 9000) receives a GitHub webhook when the workflow completes. It runs `update_brandybox.sh`, which pulls the new image and restarts the container. **You do not need to SSH and run pull/up manually.**

---

## Option 1 — 1. Trigger the image build on GitHub

Do **one** of the following:

- **Push** backend changes to `master` or `main` (workflow runs automatically).
- **Publish a release** (workflow runs for that event).
- **Run the workflow manually**: GitHub → Actions → **Publish Backend to GHCR** → Run workflow.

Wait for the workflow to finish successfully in the Actions tab.

---

## Option 1 — 2. Verify the Pi updated (after a timeout)

The webhook calls the Pi when the workflow completes; the listener runs `update_brandybox.sh` in the background. After **about 2–3 minutes** (workflow done → webhook delivery → pull + restart), verify that the update actually happened.

**Option A — Check webhook.log on the Pi**

SSH in and inspect the last lines of `backend/webhook.log`:

```bash
ssh pi 'tail -30 ~/brandyBox/backend/webhook.log'
```

You should see:

- A line indicating the webhook was received and an update was triggered (e.g. from the listener: "Neues Package bereit. Starte Update..." or similar).
- Lines from `update_brandybox.sh`: "Pulling latest image and restarting backend..." and "Backend updated."

If the webhook is not configured or the listener isn’t running, you won’t see these lines; in that case use **Option 2** (direct update) below or the main README.

**Option B — Check backend health**

From your PC (Pi at **192.168.0.150**, port from your setup, e.g. 8081):

```bash
sleep 120
curl -s http://192.168.0.150:8081/health
```

Expected: `{"status":"ok"}`. This confirms the backend is up; for proof that the *update* ran, use Option A.

---

## Option 2 — Direct update (build from source on the Pi, without GitHub/GHCR)

Use this when you want to **build and run from code on the Raspberry Pi**—no GHCR, no webhook (e.g. **direct update**, **build from source**, **without GitHub**, **without GHCR**, **test build**).

1. **SSH into the Pi** (from your PC, Pi at **192.168.0.150**):

   ```bash
   ssh pi
   ```
   Or with a key: `ssh -i ~/.ssh/your_key pi@192.168.0.150`.

2. **Pull code, build image, restart** (repo path `~/brandyBox`; change if different):

   ```bash
   cd ~/brandyBox
   git fetch origin && git pull origin master
   cd backend
   docker compose build --no-cache
   docker compose up -d
   ```

   Do **not** overwrite `backend/.env` when pulling.

3. **Verify** (after ~15 s):

   ```bash
   curl -s http://localhost:8081/health
   ```
   Expected: `{"status":"ok"}`. From your PC: `curl -s http://192.168.0.150:8081/health`.

**One-liner from your PC:**

```bash
ssh pi 'cd ~/brandyBox && git fetch origin && git pull origin master && cd backend && docker compose build --no-cache && docker compose up -d'
```

Then check health: `sleep 15 && curl -s http://192.168.0.150:8081/health`.

---

## Summary

| Mode | Where | Action |
|------|--------|--------|
| **Option 1 — GHCR** | GitHub | Trigger build (push / release / workflow_dispatch); Pi updates via webhook. Verify with `tail -30 ~/brandyBox/backend/webhook.log` and/or health curl after ~2–3 min. |
| **Option 2 — Direct** | On Pi (SSH) | `cd ~/brandyBox` → `git pull` → `cd backend` → `docker compose build --no-cache` → `docker compose up -d`. No GitHub/GHCR. |

- **Option 1** image: `ghcr.io/markusbrand/brandybox-backend:latest`. Webhook + listener: see main [README](../../README.md) and [Backend overview](../../docs/backend/overview.md).
- **Option 2**: use when you need a local/test build or have no GHCR access. Keep `backend/.env` safe.

This command is available in chat as `/install-brandybox-server`. Say e.g. **direct update**, **build from source**, **without GHCR**, or **test build** to get Option 2.
