# Stress × Schedule + Wearable Implementation Plan

> **For agentic workers:** follow the Autonomy Contract from
> `plans/2026-07-05-overnight-fable-handoff.md` (TDD per unit, migration per
> model change, no secrets, suite green per phase, decisions to OVERNIGHT-LOG).
> Base branch: `feat/pacing-model`. One `feat/*` branch + PR per phase.

Spec: `docs/superpowers/specs/2026-07-05-stress-schedule-wearable-design.md`

---

## Phase A — `feat/wellness-ingestion` (backend)

1. Model `WellnessSample` (id, recorded_at tz-aware indexed, kind str(16),
   value float, source str(16), unique (source, kind, recorded_at)) +
   Alembic migration + drift guard green.
2. `POST /wellness/ingest` — batch list[{recorded_at, kind, value, source}],
   idempotent upsert, returns {"ingested": n, "duplicates": m}. Router
   `app/routers/wellness.py`, schemas `WellnessSampleIn/BatchIn`.
3. Daily roll-up task `app/wellness.py::rollup_daily(db, days=14)` — sleep
   samples → DailySummary.sleep_duration_min/sleep_score; resting_hr samples →
   DailySummary.resting_hr. Celery beat daily 04:30 UTC + called after ingest.
4. Tests: ingest idempotency, validation, roll-up fills DailySummary, existing
   conditions strip payload picks it up (dashboard test extension).

**Gate:** suite green.

## Phase B — `feat/calendar-sync` (backend, ICS-first)

1. Deps: `icalendar`, `recurring-ical-events` (pin in requirements.txt).
2. Model `CalendarEvent` (id, start/end tz-aware, busy_status str(16),
   attendee_count int|None, is_recurring bool, subject_hash str(64), source
   str(16) default "ics", unique (source, subject_hash, start)) + migration.
3. Settings: `calendar_ics_url: str = ""` (+ `.env.example` entry with the
   Outlook publish-calendar instructions as comments).
4. `app/calendar_sync.py`: fetch ICS (httpx, mocked in tests with FakeResponse),
   expand recurrences over a ±30-day window, upsert events; salted hash of
   subject via `hashlib.sha256(salt + subject)` — salt from SECRET-less env or
   constant documented as non-secret dedup aid; store NO raw subjects.
5. `meeting_load(events, days)` aggregation: per-day minutes, per-hour
   histogram, max back-to-back streak, first-meeting hour, after-hours count.
6. Endpoints: `POST /integrations/calendar/sync` (manual), status included in
   `GET /integrations/status` (third provider entry, `connected` = URL set +
   last sync). Celery beat hourly.
7. Tests: fixture ICS (incl. a weekly RRULE event), sync idempotent, recurrence
   expansion correct, meeting_load numbers verified by hand, no raw subject
   stored anywhere (grep the DB row).

**Gate:** suite green.

## Phase C — `feat/stress-profile` (backend analysis)

1. `app/stress_profile.py` pure module: `hourly_profile`, `schedule_overlay`
   with the four findings from the spec (each with a targeted fixture test:
   fires + does-not-fire).
2. `GET /insights/stress-profile` (insights.py) over last 30 days.
3. `chat_service.build_context` += compact `"stress_profile"`;
   `report_generator.build_week_summary` += `"schedule_stress"`; SYSTEM_PROMPT
   line; fallback report mentions finding count.
4. Tests: endpoint shape, chat context key, report summary block, prompt
   guard (existing report tests stay green).

**Gate:** suite green.

## Phase D — `feat/health-connect` (Android — needs a physical device to verify)

1. Dep `androidx.health.connect:connect-client`; permissions in manifest
   (READ_SLEEP, READ_HEART_RATE, READ_RESTING_HEART_RATE + stress-adjacent
   types where available).
2. `data/wellness/HealthConnectReader.kt` (availability-guarded like
   PushRegistrar), `WellnessRepository.pushSamples()` → `/wellness/ingest`,
   WorkManager periodic sync (6h) + manual SYNC NOW row in Settings.
3. Settings screen: HEALTH CONNECT row becomes live (AVAILABLE/UNAVAILABLE/
   LAST SYNC), replacing the "LATER STEP" stub.
4. Verification is on-device only — code review + brace checks in sandbox,
   flagged in PROGRESS.md.

## Phase E — optional `feat/oura-sync` (only if an Oura ring is purchased)

Vendor adapter like strava.py: personal access token in .env, poll daily +
intraday endpoints, map to WellnessSample kinds, reuse ingest/rollup path.
Skip entirely for a Health-Connect-only device.

---

## Sequencing / dependencies

A is the foundation (C reads samples). B independent of A. C needs A (+B for
overlay findings; degrade to hourly_profile-only when no calendar). D feeds A
from a real device. Recommended order: A → B → C (pure backend, fully testable
offline — one working session), then D when the device exists.
