# Crux

**Training analytics for an athlete who trains three different ways.** Crux pulls your workouts from Strava and your listening history from Spotify, then uses an LLM to write a weekly analysis and answer questions about your training, in an Android app.

It is built around one athlete's mix of training: **sprint and anaerobic power**, **aerobic endurance**, and **loaded sustained effort** (mountaineering prep). Most training apps treat these the same. Crux analyses them separately and flags where they interfere with each other.

## What it does

- **Syncs Strava activities** automatically (every 30 minutes) and classifies each as sprint, aerobic or loaded work.
- **Generates a weekly report** (Mondays) from per-mode training totals, written by an LLM, with a push notification when it's ready.
- **Chat about your training**: the LLM gets a 28-day snapshot of your data plus recent conversation.
- **Spotify mood tracking**: connects what you listen to with how your sessions go.
- **Interference checks**: deterministic rules flag session sequences that work against each other (for example, a long aerobic session within 48 hours before a sprint session). The LLM then explains why the flag matters.
- **Recovery and stress signals**: daily readiness from sleep, resting heart rate and training load, plus a work-calendar overlay that looks for links between meeting load and stress or sleep.
- **Voice-note logging** in Romanian or English, extracted by keyword rules first and an LLM fallback second.
- **Mountaineering objective**: set a summit and a date, and track vertical gain and days to go.

Everything with an LLM also has a deterministic offline fallback, so the pipeline runs end to end, and is testable, without an API key.

## How it's built

| Part | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0, PostgreSQL, Alembic migrations, Celery + Redis |
| Android app | Kotlin, Jetpack Compose, Retrofit, StateFlow ViewModels |
| LLM | Provider abstraction over OpenRouter or the Anthropic API |
| Integrations | Strava and Spotify (OAuth), Health Connect, calendar (ICS feed), Firebase Cloud Messaging |
| Deployment | Docker Compose, Caddy (TLS), DigitalOcean App Platform spec |

A few design choices:

- **Sync is idempotent**: activities upsert on `(source, external_id)` and listening on `played_at`, so re-syncing never duplicates data.
- **LLMs explain, code decides**: correlations, interference flags and readiness are computed with plain tested functions, and the model is only asked to interpret them. Findings are reported with their numbers and without causal claims.
- **Honest about missing data**: when wearable data isn't flowing, readiness shows a low-data state instead of inventing a score. The mountaineering pacing estimator is marked as needing calibration on real data.
- **Schema safety**: migrations run at startup, and a test fails if the models and migrations drift apart.
- **Test coverage**: a pytest suite with one module per backend feature.

## Project layout

```
backend-fastapi/    API, sync jobs, report and chat services, migrations, tests
android-native/     Kotlin / Jetpack Compose app
docs/               Design system (DESIGN.md), progress log, backlog
```

The Android UI follows a "meet sheet" design system, documented in [docs/DESIGN.md](docs/DESIGN.md).

## Run it

```bash
cd backend-fastapi
cp .env.example .env     # add Strava / Spotify credentials and an LLM key (optional)
docker compose up --build
```

API docs are at http://localhost:8000/docs. Run the tests with `python -m pytest -q`.

For the app, open `android-native/` in Android Studio. The emulator reaches the backend at `http://10.0.2.2:8000/`.

Deployment instructions are in [backend-fastapi/docs/DEPLOY.md](backend-fastapi/docs/DEPLOY.md) (full droplet stack) and `.do/app.yaml` (App Platform).

<details>
<summary>Notes on configuration</summary>

- **Single user, no app auth.** Strava and Spotify OAuth tokens are stored per provider and refreshed automatically.
- **Spotify audio features** (valence and energy) are fetched best-effort. Spotify restricted that endpoint for newer apps, so mood degrades to "no data" instead of failing.
- **Hand-timed sprint splits** can't come from Strava, so they are added through `POST /activities`.
- **Push notifications** need a Firebase project: add `google-services.json` to `android-native/app/`, uncomment the two `google-services` plugin lines in the Gradle files, and set `FCM_SERVICE_ACCOUNT_JSON_PATH` for the backend. Without it, push is a logged no-op and never breaks report generation.
- **Schema changes**: edit the models, run `alembic revision --autogenerate -m "..."`, and review the migration.

</details>
