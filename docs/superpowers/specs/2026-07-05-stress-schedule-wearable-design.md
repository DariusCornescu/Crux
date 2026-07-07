# Design: Stress × Schedule correlation + wearable recovery ingestion

Date: 2026-07-05
Scope: backend (`backend-fastapi/`), Android later phases
Status: spec for review — implementation as new `feat/*` PRs after approval

## Goal

Answer one question with data: **"When during the day am I most stressed, and
does my work schedule explain it?"** — then feed that into the weekly report
so training guidance accounts for work load (e.g. don't schedule sprint
sessions after the 3-hour Wednesday meeting block).

Two new data sources make that possible:

1. **Work calendar** (Microsoft Teams/Outlook, company M365) → the *exposure*:
   meeting density per hour of day, back-to-back streaks, after-hours meetings.
2. **Wearable** (watch/ring/bracelet) → the *response*: intraday stress/HRV,
   resting HR, sleep quality. Also finally fills the empty `DailySummary`
   sleep/RHR columns that the conditions strip and reports already expect.

## Constraint that shapes the calendar design: company tenant

The account is a **work M365 account**. A personal Graph app registration
likely needs tenant admin consent — a hard blocker we don't control. So:

- **Primary path: ICS published-calendar feed.** Outlook web → Settings →
  Calendar → Shared calendars → Publish a calendar → copy the ICS URL. This is
  a user-level feature, no OAuth, no admin consent; the backend polls the URL
  hourly like any RSS feed. Read-only, revocable by unpublishing.
- **Upgrade path (later, optional): Microsoft Graph OAuth** behind the same
  internal interface, if the tenant allows it. Nothing downstream changes.
- **If the tenant also disables calendar publishing**: manual `.ics` export
  upload endpoint as a last resort (documented, not built initially).

## Privacy stance (calendar contents on a personal VPS)

We never need meeting titles or attendee names for the analysis. Stored per
event: `start`, `end`, `busy_status`, `is_recurring`, `attendee_count` (when
available), and a salted **hash** of the subject (dedup only). Raw subjects
are NOT stored, and the LLM sees only aggregates ("3.5h meetings, longest
streak 4 back-to-back"), never event details.

## Wearable: device-agnostic core + adapters

No device owned yet (recommendation below). The design assumes devices change:

- **Core model `WellnessSample`** — `(recorded_at, kind, value, source)` where
  `kind ∈ {stress_score, hrv_ms, resting_hr, sleep_stage, sleep_score,
  body_battery, spo2}` and `source ∈ {health_connect, oura, fitbit, manual}`.
  Intraday resolution is the point — hour-of-day stress needs timestamps, not
  daily averages.
- **Ingestion endpoint** `POST /wellness/ingest` (batch, idempotent on
  `(source, kind, recorded_at)`) — anything that can POST JSON can feed it.
- **Adapter A (first): Android Health Connect.** Nearly every vendor (Garmin,
  Samsung, Fitbit, Polar, Xiaomi, Whoop) writes into Health Connect; the
  Splitrail app reads new samples and pushes batches. One integration, any
  device. Limitation: sync happens when the phone app runs (WorkManager
  periodic job).
- **Adapter B (optional, device-dependent): vendor cloud polling** — only if
  the chosen device has an open API (Oura/Fitbit/Whoop). Backend-side like
  Strava/Spotify; no phone dependency.
- **Roll-up**: a daily Celery task aggregates samples into the existing
  `DailySummary` (sleep_duration_min, sleep_score, resting_hr) — the
  conditions strip and weekly report start showing real values with zero UI
  changes.

### Device recommendation (asked for)

For Splitrail's needs — sleep, HRV/stress, recovery; activities already come
from Strava — data quality and API access matter more than wrist GPS:

- **Best fit: Oura ring.** Best-in-class sleep/HRV/readiness + daytime stress,
  and a clean open cloud API (personal token) → Adapter B works without the
  phone. Unobtrusive under a sprint session or a ruck strap.
- **Best all-in-one: Garmin** (Forerunner 265/965 or Instinct for mountains).
  Body Battery ≈ stress, strong HRV status, and it doubles as the training/
  navigation watch — but cloud API is partner-gated, so it syncs via Health
  Connect (Adapter A, phone-mediated).
- Avoid for this purpose: Fitbit (declining ecosystem), Whoop (subscription,
  data behind membership).

Either choice works with this design; Oura unlocks the nicer architecture.

## Analysis: `app/stress_profile.py` (pure module, like interference.py)

- `hourly_profile(samples, days=30)` → per hour-of-day (0–23) × day-class
  (workday/weekend): avg stress score (or inverted-HRV z-score when the device
  gives HRV only), sample count.
- `schedule_overlay(events, samples, days=30)` → deterministic findings, each
  `{code, message, evidence}`:
  - `stress_peak_hours` — top-2 stress hours vs daily mean.
  - `meeting_load_correlation` — stress on heavy-meeting days (≥p75 meeting
    minutes) vs light days, workdays only.
  - `after_hours_meetings_sleep` — late meetings (ending ≥19:00) vs that
    night's sleep score/duration.
  - `morning_meeting_rhr` — days whose first meeting <09:00 vs resting HR.
- Exposure: `GET /insights/stress-profile`; compact block into
  `chat_service.build_context` under `"stress_profile"`; weekly report summary
  gains `"schedule_stress"` + a SYSTEM_PROMPT line ("Use the schedule/stress
  data when advising session placement — cite hours and numbers").
- All correlations are deterministic and labeled observational — no causal
  claims; the LLM is instructed likewise.

## Non-goals

- Writing to the calendar, meeting content analysis, Teams chat/presence.
- Medical-grade stress claims. This is self-quantification, not diagnostics.
- Multi-user.

## Dependency notes

- New python deps: `icalendar` + `recurring-ical-events` (RRULE expansion is
  genuinely hard; do not hand-roll).
- Android: `androidx.health.connect:connect-client` (Adapter A phase).
- No conflicts with the in-flight PR stack — builds on top of
  `feat/pacing-model`.
