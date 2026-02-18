# install-brandybox-server

Detailed Linux terminal commands to **update and upgrade the Brandy Box backend** on the Raspberry Pi. Run these from your **Garuda Linux PC**; the backend runs in Docker on the Pi at **192.168.0.150** (SSH with public key, no password).

---

## 1. SSH into the Raspberry Pi

From your Garuda PC:

```bash
ssh pi
```

- Replace `pi` with your Pi username if different.
- If you use a specific key: `ssh -i ~/.ssh/your_key pi@192.168.0.150`.
- You should get a shell on the Pi without being asked for a password.

---

## 2. Go to the repo and pull the latest code

On the Pi (inside the SSH session):

```bash
cd ~/brandyBox
git fetch origin
git status
git pull origin master
```

- If your default branch is `main` instead of `master`, use: `git pull origin main`.
- If `git status` shows local changes you don’t want to keep: `git checkout -- .` then pull again, or `git stash` then `git pull` then `git stash pop` if you need to reapply local changes.

---

## 3. Rebuild and restart the backend container

Still on the Pi, from the repo root:

```bash
cd ~/brandyBox/backend
docker compose build --no-cache
docker compose up -d
```

- `build --no-cache` forces a full rebuild so new code and dependency changes are applied.
- `up -d` starts the container in the background. Existing `.env` in `backend/` is unchanged.

---

## 4. Check that the backend is up

Wait a few seconds for the app to start, then:

```bash
sleep 15
curl -s http://localhost:8081/health
```

- Expected: `{"status":"ok"}` (or similar JSON with status).
- If the service uses another port (e.g. 8082), use that port in the URL.

Optional: check container status and recent logs:

```bash
docker compose ps
docker compose logs --tail 50
```

- If the container is **Exited**, run `docker compose logs` and fix any errors (e.g. missing `BRANDYBOX_JWT_SECRET` in `.env`).

---

## 5. Exit SSH

```bash
exit
```

---

## One-liner (from Garuda PC)

To do everything in one go from your Garuda PC (single SSH session):

```bash
ssh pi@192.168.0.150 'cd ~/brandyBox && git fetch origin && git pull origin master && cd backend && docker compose build --no-cache && docker compose up -d'
```

Then wait ~15 s and check health from your PC:

```bash
sleep 15
curl -s http://192.168.0.150:8081/health
```

---

## Summary

| Step | Where | Command |
|------|--------|---------|
| Connect | Garuda PC | `ssh pi@192.168.0.150` |
| Update code | On Pi | `cd ~/brandyBox` → `git fetch` → `git pull origin master` (or `main`) |
| Rebuild & run | On Pi | `cd ~/brandyBox/backend` → `docker compose build --no-cache` → `docker compose up -d` |
| Verify | On Pi (or from PC) | `curl -s http://localhost:8081/health` or `http://192.168.0.150:8081/health` |

- Repo path on Pi is assumed to be `~/brandyBox`; change it if your clone is elsewhere.
- Do **not** overwrite `backend/.env` when pulling; keep your JWT secret, SMTP, and admin settings.

This command is available in chat as `/install-brandybox-server`.
