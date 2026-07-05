# Splitrail

Personal training analytics for a three-mode athlete: sprint/anaerobic power,
aerobic endurance, and loaded sustained effort (mountaineering prep).

## What this app is

I'm a former national 60m sprint champion (PB 6.91s) coming back into shape
after 8 months of reduced training — rebuilding aerobic base and preparing for
mountaineering. My training spans three distinct physiological modes:

- **explosive** — sprint / anaerobic power (neural work)
- **aerobic** — sustained endurance (engine work)
- **loaded** — rucking/hiking under load (structural work)

Splitrail ties training data (Strava), sleep/recovery, and mood (via Spotify
listening history) into one analyzed picture, with an LLM generating weekly
insight reports and answering on-demand questions about my own data.

## Architecture

- **Backend**: FastAPI + Celery + Redis + Postgres, Dockerized
  (`backend-fastapi/`)
- **Android client**: native Kotlin, Jetpack Compose (`android-native/`)
- **Integrations**: Strava API (OAuth) for activities, Spotify API (OAuth) for
  listening history + audio features, Android Health Connect later
- **LLM**: weekly scheduled analysis reports (Celery → structured summary →
  LLM → stored report → push notification) plus an on-demand chat endpoint

## Build order

1. ☐ Backend skeleton + Android skeleton (nav shell)
2. ☐ Strava OAuth + activity sync + connect-account flow
3. ☐ Dashboard on real activity data
4. ☐ Spotify OAuth + listening/mood sync + mood chart
5. ☐ LLM weekly report generation + Reports screen
6. ☐ Chat endpoint + chat UI
7. ☐ Push notifications + polish

Feature backlog beyond the build order: [docs/BACKLOG.md](docs/BACKLOG.md).
Design system ("MEET SHEET" — an instrument-panel / timing-system aesthetic,
not a generic fitness app): [docs/DESIGN.md](docs/DESIGN.md).
