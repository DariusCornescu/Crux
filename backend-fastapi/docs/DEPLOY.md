# Deploying Crux to a DigitalOcean Droplet

The backend is Dockerized. Production runs the same compose stack plus a Caddy
reverse proxy that terminates HTTPS with an automatic Let's Encrypt certificate.
No git is used — code is copied to the Droplet with `scp`.

## Prerequisites
- A domain you control.
- A DigitalOcean account.

## 1. Create the Droplet
- Create a Droplet: Ubuntu LTS, Basic plan (1 GB+ RAM is enough), add your SSH key.
- Note its public IP.

## 2. Point DNS at the Droplet
- Add an `A` record: `your-domain -> <droplet IP>`.
- Wait until `ping your-domain` resolves to the IP (Caddy needs this before it
  can issue a certificate).

## 3. Install Docker on the Droplet
SSH in (`ssh root@<droplet IP>`), then:
```
curl -fsSL https://get.docker.com | sh
```
This installs Docker Engine + the Compose plugin.

## 4. Copy the backend to the Droplet
From your PC, in `PersonalApp/`:
```
scp -r backend-fastapi root@<droplet IP>:/srv/crux
```

## 5. Create secrets on the Droplet
On the Droplet, in `/srv/crux`:
- Create `.env` (copy from `.env.example`) and fill in real values:
  - `OPENROUTER_API_KEY=<your key>`
  - `POSTGRES_PASSWORD=<a strong password>`
  - Strava/Spotify client IDs + secrets
  - `FCM_SERVICE_ACCOUNT_JSON_PATH=/srv/secrets/fcm-service-account.json`
- Create `secrets/fcm-service-account.json` (paste the Firebase key) if using push.

## 6. Set the real domain
Edit `Caddyfile` and replace `your-domain.example` with your domain.

## 7. Launch
```
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
Caddy fetches the TLS cert automatically on first start (needs ports 80/443 open).
Note: the `!reset` tag in the overlay needs Docker Compose v2.24+ (get.docker.com
installs current). If an older Compose errors on it, replace `ports: !reset []`
with `ports: ["127.0.0.1:8000:8000"]`.

## 8. Verify
```
curl https://your-domain/healthz
```
Expected: `{"status":"ok"}`.

## 9. Update OAuth redirect URIs
In the Strava and Spotify developer dashboards, change the redirect URIs to:
- `https://your-domain/integrations/strava/callback`
- `https://your-domain/integrations/spotify/callback`
Also update `STRAVA_REDIRECT_URI` / `SPOTIFY_REDIRECT_URI` in `.env` to match, then
`docker compose ... up -d` again.

## 10. Firewall
Allow only ports 22, 80, 443 (DigitalOcean Cloud Firewall or `ufw`). Postgres and
Redis stay internal to the compose network — never publish them.

## Updating later
Re-`scp` the changed files and run the compose up command again.
