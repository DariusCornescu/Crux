# PROGRESS

Session log, newest first (same convention as ListManagerApp).

## 2026-07-05 (later) — stress × schedule + wearable ingestion (Phases A-C)

Spec `superpowers/specs/2026-07-05-stress-schedule-wearable-design.md`, TDD
throughout, suite 58 → **75 passed**, two new migrations (wellness_samples,
calendar_events). Three new PRs on the stack:
- `feat/wellness-ingestion` — device-agnostic intraday WellnessSample +
  idempotent `POST /wellness/ingest`; daily roll-up finally fills
  DailySummary sleep/RHR (conditions strip shows real data).
- `feat/calendar-sync` — work calendar via published-ICS feed (no OAuth/admin
  consent on the company tenant), RRULE expansion, privacy-preserving storage
  (hashed subjects, no titles), meeting-load aggregation, hourly beat.
- `feat/stress-profile` — hour-of-day stress (vendor score or inverted-HRV
  fallback), 4 deterministic schedule findings (peak hours, heavy-meeting
  stress delta, late-meetings→sleep, early-meetings→RHR),
  `GET /insights/stress-profile`, chat context + weekly report integration.

**Next:** Phase D (Android Health Connect reader — needs a physical device),
optional Phase E (Oura adapter if the ring is bought), Android UI for
stress/insights. Set `CALENDAR_ICS_URL` + `HOME_TIMEZONE` in `.env` to
activate calendar sync.

## 2026-07-05 — overnight autonomous run (handoff plan, Phases 0–5)

All five phases of `docs/superpowers/plans/2026-07-05-overnight-fable-handoff.md`
implemented TDD-first; suite went 18 → **55 passed**; two new migrations
(`voice_logs`); no secrets touched; nothing deployed. Decisions in
`docs/superpowers/OVERNIGHT-LOG.md`; your to-dos in
`docs/superpowers/MORNING-CHECKLIST.md`. Highlights: `app/llm.py` provider
abstraction (OpenRouter default), voice-log capture + bilingual two-stage
extraction, subjective/interference/audio-priming inputs feeding the weekly
report, pacing estimator, deploy files (Caddy + prod overlay + DEPLOY.md),
Android pointed at HTTPS placeholder domain (TODO(domain)).

## 2026-07-04 — steps 6–7 (chat + push + polish)

**What changed**
- Step 6: `app/chat_service.py` — 28-day data context + last 10 turns →
  Claude (offline-mode deterministic reply without API key); `POST /chat`,
  `GET /chat/history`. Android: ChatRepository/ChatViewModel with optimistic
  sends, timing-sheet message rows (no bubbles), BasicTextField input bar,
  assistant replies rendered via shared MarkdownLite.
- Step 7: `device_tokens` table (migration `c2257a2f00bd`), `POST /devices`
  (idempotent), `app/push.py` (firebase-admin, best-effort — never breaks
  report generation), wired into the Monday report task. Android:
  SplitrailMessagingService + PushRegistrar (guarded no-ops until
  google-services.json is added; setup steps in README), POST_NOTIFICATIONS
  permission, firebase-messaging dependency (plugin lines commented).
- Polish: MarkdownLite moved to ui/components (shared by Reports + Chat);
  Dashboard shows a red "DEMO SIGNAL" tag while the backend serves demo data
  (`demo` flag added to /dashboard/summary).
- Backend tests: 18 passing.

**What's next**
- First device run: Firebase setup (README), notification permission request
  UX, real Strava/Spotify credentials.
- Night-ops (inverted) theme variant; Health Connect (sleep/HR) integration.
- Consider Room cache + offline queue once real usage shows gaps.

**Open questions**
- Notification tap → deep link into the specific report (needs nav deep-link
  wiring; report_id already rides in the FCM data payload).

## 2026-07-04 — steps 2–5 + reorganization to ListManagerApp layout

**What changed**
- Monorepo reorganized: `backend/` → `backend-fastapi/`, `android/` →
  `android-native/`; `app/db.py` → `app/database.py` with a constraint
  naming convention; Alembic added (baseline `a6894f76515b`), migrations run
  at startup, drift-guard test added.
- Step 2: `app/strava.py` — OAuth code exchange, token refresh, idempotent
  activity sync with name-first type classification. Beat every 30 min.
- Step 4: `app/spotify.py` — OAuth, recently-played sync (idempotent on
  played_at), audio-features best-effort (endpoint restricted for post-2024
  Spotify apps → valence/energy may stay NULL), daily mood aggregation.
- Step 5: `app/report_generator.py` — weekly per-mode aggregate → Claude API
  → Report row (deterministic fallback without API key). Beat Mon 05:00 UTC,
  manual `POST /reports/generate`.
- Dashboard payload gained `mood_trend` (14 days).
- Android rebuilt in ListManagerApp package structure: `network/`
  (DTOs/SplitrailApi/RetrofitClient/ApiConfig), `data/model` +
  `data/repository` (RepoResult adapted), `ui/viewmodel` (UiState +
  StateFlow), `ui/navigation/NavGraph`, screens: Dashboard (live API,
  loading/error strips, MoodTrace), Reports list + detail (MarkdownLite
  renderer), Settings (connect via browser, sync now, status).
- Backend tests: 13 passing (`pytest -q`).

**What's next**
- Step 6: chat endpoint (context assembly + Claude) + chat UI.
- Step 7: FCM push on new report; night-ops theme variant.
- First real device run: set `ApiConfig.BASE_URL`, connect Strava, verify
  classification against actual activity titles.
- Consider Room cache + offline queue (ListManagerApp pattern) once real
  usage shows gaps.

**Open questions**
- Spotify audio-features access: if the app registration can't get it,
  consider inferring mood from track/artist via a nightly Claude batch
  instead.
- `strength` → `explosive` mode mapping is crude; revisit per-session.

## 2026-07-04 (earlier) — step 1

Skeletons scaffolded: FastAPI + Celery + Redis + Postgres compose; Android
Compose app with MEET SHEET design system, Rail tape + three instruments on
sample data. Design tokens in docs/DESIGN.md.
