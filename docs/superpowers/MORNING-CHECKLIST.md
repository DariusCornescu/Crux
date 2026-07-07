# MORNING-CHECKLIST — human-gated steps, in order

Everything below needs you (accounts, money, hardware). The code side is done:
55 tests green, migrations consistent. Details in `docs/superpowers/OVERNIGHT-LOG.md`.

## 0. Five-minute sanity check (recommended)
```
cd backend-fastapi
python -m pytest -q                      # expect: 55 passed
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet && echo VALID
```
The compose check could not run overnight (no docker in the sandbox) — this is
the one deferred gate. If `!reset` errors (Compose < v2.24), see the note in
`docker-compose.prod.yml` / `docs/DEPLOY.md`.

## 1. Deploy the backend (follow `backend-fastapi/docs/DEPLOY.md`)
1. Create the DigitalOcean Droplet (Ubuntu LTS, 1 GB+, your SSH key).
2. Point your domain's `A` record at the Droplet IP; wait for DNS.
3. `ssh root@<ip>` → `curl -fsSL https://get.docker.com | sh`
4. From `PersonalApp/`: `scp -r backend-fastapi root@<ip>:/srv/splitrail`
5. On the Droplet: create `.env` from `.env.example` — set `OPENROUTER_API_KEY`
   (get one at https://openrouter.ai/keys), a strong `POSTGRES_PASSWORD`,
   Strava/Spotify credentials, FCM path if using push.
6. Edit `Caddyfile`: replace `your-domain.example` with the real domain.
7. `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
8. `curl https://<domain>/healthz` → `{"status":"ok"}`

## 2. OAuth redirect URIs
In the Strava and Spotify developer dashboards, set redirect URIs to
`https://<domain>/integrations/strava/callback` and
`https://<domain>/integrations/spotify/callback`; mirror them in `.env`, then
re-run the compose up command.

## 3. Android
1. `network/ApiConfig.kt`: replace `https://your-domain.example/` (TODO(domain))
   with the real domain. (Cleartext flag is already removed.)
2. Build + install: `./gradlew assembleDebug && adb install -r app/build/outputs/apk/debug/app-debug.apk`
   — first compile of the new code; expect possibly minor fixes (never compiled
   here, no Android SDK).
3. Grant notification permission on the phone (Android 13+).
4. FCM (optional now): google-services.json + uncomment the two plugin lines —
   see README "Enabling FCM".

## 4. Real end-to-end validation (needs the key + deploy)
- `POST /reports/generate` with `OPENROUTER_API_KEY` set → real LLM report
  (check the interference/subjective sections read sensibly).
- Chat a question; check `audio_priming` shows up in answers about music.
- `POST /voice-logs` with a long ambiguous transcript → `extraction_method="llm"`.

## What was built overnight (summary)
- **Phase 0**: `app/llm.py` provider abstraction (OpenRouter default via openai
  SDK, Anthropic optional); report + chat refactored onto it; invalid model ID
  fixed; Caddyfile + docker-compose.prod.yml + docs/DEPLOY.md; Android HTTPS edits.
- **Phase 1**: `voice_logs` table + migration; bilingual two-stage extraction
  (`app/voice_extract.py`); POST/GET `/voice-logs` with same-day activity linkage.
- **Phase 2**: `app/correlations.py` (`heavy_legs_after_big_vert`); weekly report
  now carries a `subjective` block + flags; prompt extended.
- **Phase 3**: `app/interference.py` (3 sequencing rules) +
  `app/knowledge/concurrent_training.md` fed to the report LLM as REFERENCE.
- **Phase 4**: `app/audio_priming.py`; `GET /insights/audio-priming`; chat
  context includes the priming comparison. Playlist auto-suggest: deferred.
- **Phase 5**: `app/pacing.py` + `POST /pacing/estimate` — synthetic-fixture
  heuristic, clearly labeled as needing real-data calibration.
- Also fixed pre-existing corruption in `docker-compose.yml` (truncated tail).

Skipped/deferred: playlist auto-suggest (per handoff), real `docker compose
config` gate (no docker overnight — step 0 above).
