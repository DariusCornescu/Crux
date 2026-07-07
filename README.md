# Splitrail

Personal training analytics for a three-mode athlete: sprint/anaerobic power,
aerobic endurance, and loaded sustained effort (mountaineering prep). Strava +
Spotify in; Claude-generated weekly analysis and on-demand chat out.

Monorepo layout mirrors [ListManagerApp](https://github.com/DariusCornescu/ListManagerApp):

- `backend-fastapi/` — FastAPI backend. App package in `backend-fastapi/app/`
  (flat service modules `strava.py` / `spotify.py` / `report_generator.py`,
  thin `routers/`, Alembic migrations applied at startup, pytest suite).
- `android-native/` — Android app (Kotlin, Jetpack Compose). Packages:
  `network/` (DTOs, Retrofit), `data/model` + `data/repository`,
  `ui/{screens,components,navigation,viewmodel,theme}`, `util/`.
- `docs/` — DESIGN.md (MEET SHEET design system), PROGRESS.md (session log).

## Commands

- Backend run: `cd backend-fastapi && cp .env.example .env && docker compose up --build`
  (API docs: http://localhost:8000/docs)
- Backend tests: `cd backend-fastapi && python -m pytest -q`
- Android build: open `android-native/` in Android Studio (generates the Gradle
  wrapper), or `gradle wrapper && ./gradlew assembleDebug`

## Stack facts

- DB: PostgreSQL (Docker) / SQLite in tests, SQLAlchemy 2.0. **Alembic** manages
  schema: migrations in `backend-fastapi/alembic/versions/`; app runs
  `upgrade head` at startup (disable via `RUN_MIGRATIONS=false`). To change
  schema: edit models → `alembic revision --autogenerate -m "..."` → review →
  the drift-guard test in `tests/test_migrations.py` fails if models and
  migrations diverge. Constraint naming convention lives on `Base.metadata`.
- Single user, no app auth. OAuth tokens for Strava/Spotify stored in
  `oauth_tokens` (one row per provider), auto-refreshed.
- Strava sync: Celery beat every 30 min + `POST /integrations/strava/sync`;
  idempotent upsert on `(source, external_id)`; type classification is
  name-first ("ruck"/"tempo"/"sprint" in the title), then sport type. Hand-timed
  sprint splits enter via `POST /activities` — Strava won't carry them.
- Spotify sync: every 45 min + manual; idempotent on `played_at`. Audio
  features (valence/energy) are fetched best-effort — Spotify restricted that
  endpoint for post-2024 apps, so mood degrades to "no data" instead of failing.
  Daily aggregates land in `daily_summaries.mood_*`.
- Weekly report: Celery beat Mon 05:00 UTC + `POST /reports/generate`.
  Aggregates the week per effort mode → Claude API (`ANTHROPIC_API_KEY`,
  model via `ANTHROPIC_MODEL`) → Markdown + highlights JSON. Without a key it
  stores a deterministic fallback so the pipeline stays testable end to end.
- Android: Retrofit/Gson + StateFlow ViewModels (no Room cache yet — add the
  ListManagerApp offline queue pattern when needed). Emulator base URL
  `http://10.0.2.2:8000/` in `network/ApiConfig.kt`.
- Chat: `POST /chat` + `GET /chat/history`. `app/chat_service.py` hands Claude a
  JSON snapshot (28-day per-mode totals, dailies, latest report highlights) plus
  the last 10 turns. Without a key it replies with a deterministic data snapshot.
- Push: weekly-report Celery task fires FCM to tokens registered via
  `POST /devices`. Backend needs `FCM_SERVICE_ACCOUNT_JSON_PATH`; unconfigured
  push is a logged no-op and never breaks report generation.

## Enabling FCM (step 7 one-time setup)

1. Create a Firebase project, add Android app `com.darius.splitrail`, download
   `google-services.json` into `android-native/app/`.
2. Uncomment the two `google-services` plugin lines (root and app
   `build.gradle.kts`).
3. Download a service-account key JSON, mount it into the backend containers,
   set `FCM_SERVICE_ACCOUNT_JSON_PATH` in `.env`.
4. Grant notification permission on the device (Android 13+). The app
   registers its token automatically on start and on token rotation.

## Deploying

Two options:

- **DigitalOcean App Platform** (auto-deploy on merge to main): import
  `.do/app.yaml`, set the encrypted env vars listed inside it, and every merged
  PR redeploys the API + managed Postgres. Celery worker/beat are not part of
  the spec yet — trigger syncs/reports via their POST endpoints.
- **Droplet, full stack** (API + workers + Postgres + Redis + Caddy TLS):
  follow [backend-fastapi/docs/DEPLOY.md](backend-fastapi/docs/DEPLOY.md).

## Build order

1. ✅ Backend skeleton + Android skeleton (nav shell)
2. ✅ Strava OAuth + activity sync + connect-account flow
3. ✅ Dashboard on real activity data (demo payload until first sync)
4. ✅ Spotify OAuth + listening/mood sync + mood chart
5. ✅ Claude weekly report generation + Reports screen
6. ✅ Chat endpoint + chat UI
7. ✅ FCM push (needs Firebase config — see below) + polish

Design system: see [docs/DESIGN.md](docs/DESIGN.md).
