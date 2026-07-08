# Design: Dashboard v2 — remove GATE, agenda, daily quote, signals detail

Date: 2026-07-08. Approved by Darius (AskUserQuestion round): remove GATE entirely;
calendar stores titles; quotes are LLM-generated daily and data-aware; tap on the
top region opens a full SIGNALS screen.

## Summary

Four user-driven changes to the Dashboard experience:

1. **Remove the GATE (sprint) instrument** — the hardcoded 6.91 PB block is dead
   weight for current training. Sprint sessions remain on THE RAIL and in
   reports/chat. Android-only change; the API keeps returning `gate` (ignored).
2. **AGENDA — next 2 calendar events** in GATE's old slot, tap to expand details.
   Requires storing real meeting titles (deliberate privacy-design change, own
   server) and a new upcoming-events endpoint.
3. **Daily motivational quote** — LLM-generated from the athlete's actual week
   (via the existing `app/llm.py` provider), cached per day, deterministic static
   fallback offline. Rendered as one engraved line near the bottom.
4. **SIGNALS detail screen** — the COND strip + MoodTrace region becomes tappable
   and opens a new screen: recent ~30 tracks (time/title/artist/valence) and a
   14-day table (sleep, RHR, mood). Sleep/RHR show `--` until a wearable feeds
   data; the screen is forward-built for that.

## Scope

### A. Remove GATE (Android only)
- `DashboardScreen.kt`: drop the `GateInstrument(data.gate)` call + its hairline.
- `Instruments.kt`: `GateInstrument` composable may remain (unused) or be deleted —
  delete it and its now-unused imports to keep the file honest.
- `Constants.kt` `SPRINT_PB_SECONDS` becomes unused → delete.
- Keep `GateBlock` DTO (payload still contains it).

### B. Calendar titles + upcoming endpoint
- `app/models.py::CalendarEvent`: add `subject: Mapped[str | None] =
  mapped_column(String(256), nullable=True)` (+ Alembic migration). `subject_hash`
  stays (dedup key). Old rows keep NULL subject → UI renders "BUSY".
- `app/calendar_sync.py::parse_ics`: include `"subject": str(component.get("SUMMARY", ""))`
  in each event dict (upsert loop then persists it automatically).
- New router `app/routers/calendar.py`: `GET /calendar/upcoming?limit=2` →
  future events (`start >= now`), ordered by start, serialized as
  `[{start, end, subject, attendee_count, is_recurring}]`. Limit clamped 1..10.
- Schemas: `UpcomingEvent` in `app/schemas.py`.
- Dependency (user): publish Outlook calendar → set `CALENDAR_ICS_URL` (+
  `HOME_TIMEZONE` already defaulted) in the droplet `.env`. Hourly beat already
  syncs once configured.

### C. Daily quote
- New table `daily_quotes` (`id`, `day` Date unique indexed, `text` Text,
  `source` String(8) — "llm" | "static") + migration.
- New module `app/quotes.py`:
  - `get_today(db) -> DailyQuote`: return today's row if present; else build a
    one-line training snapshot (this ISO-week aerobic km, loaded vert, session
    count — reuse the aggregation pattern from `report_generator`/dashboard),
    call `llm.complete(system=..., max_tokens=80)` for a SHORT (≤120 chars)
    motivational line referencing the data; on `not llm.is_configured()` or any
    exception, fall back to `STATIC_QUOTES[day_of_year % len(STATIC_QUOTES)]`
    (curated list of ~12 training/mountaineering quotes, stored in the module).
    Persist + return the row. One LLM call per day maximum.
- New router `app/routers/quote.py`: `GET /quote/today` → `{day, text, source}`.

### D. Signals detail endpoint + screen
- New router `app/routers/signals.py`: `GET /signals/detail` →
  `{"recent_tracks": [last 30 ListeningSession desc: {played_at, track, artist,
  valence, energy}], "daily": [last 14 DailySummary desc: {day, sleep_min,
  sleep_score, resting_hr, mood_valence, mood_energy}]}`.
- Android: top region (ConditionsStrip + MoodTrace) wrapped in `clickable` →
  `nav.navigate("signals")`. New `SignalsScreen` (route pushed like
  `reports/{id}`, not a bottom tab): tracks list + daily table, timing-sheet
  style (hairlines, mono digits, engraved caps labels, no cards).

### Android data plumbing (B, C, D)
- DTOs + `CruxApi` endpoints (`/calendar/upcoming`, `/quote/today`,
  `/signals/detail`), repository + ViewModel additions following the existing
  `DashboardRepository`/`DashboardViewModel` patterns. Agenda + quote load
  lazily/independently so `/dashboard/summary` render is not blocked; failures
  degrade to hiding the block (no error strips for secondary content).
- AGENDA block UI: "NEXT UP" engraved label; per event one row `HH:mm–HH:mm ·
  TITLE` (Plex Mono time, Sans title, GateRed accent for today's events);
  tap toggles an inline expanded row (full title, weekday + date, duration,
  attendee count). No events / not configured → block hidden entirely.
- QUOTE UI: single Graphite line between hairlines at the Dashboard bottom;
  hidden while loading/failed.

## Out of scope
- Push notifications for meetings (separate feature, needs Firebase).
- Wearable/sleep ingestion sources (screen shows `--` until data exists).
- Logo (separate task).
- Removing `gate` from the backend payload (harmless, avoids API churn).

## Testing
- Backend TDD: upcoming-endpoint filtering/ordering/limit + subject persisted
  through `parse_ics`→`sync_ics` (existing ICS fixtures in `tests/test_calendar_sync.py`);
  quote caching (2nd call same day = same row, no 2nd LLM call), offline static
  fallback determinism; signals payload shape + ordering; migrations drift-guard.
- Android gate: `gradlew.bat assembleDebug` BUILD SUCCESSFUL.
- Post-deploy: `/calendar/upcoming` returns events once ICS is configured;
  `/quote/today` returns a line (static until LLM key present — prod has key);
  SIGNALS screen shows real tracks.

## Rollout
Merge → droplet `git pull` + compose up (migrations auto-run) → user publishes
Outlook ICS and sets `CALENDAR_ICS_URL` in `/srv/crux/backend-fastapi/.env` →
compose up again → rebuild APK → adb install → verify on phone.

## Risks
- ICS `SUMMARY` may be empty/missing → subject NULL → "BUSY" row (accepted).
- LLM quote latency on first request of the day (~1-3s) — acceptable for a
  lazily-loaded secondary block; result cached for the rest of the day.
- Old calendar rows lack titles until the next hourly sync upserts them
  (upsert refreshes all events in the ±30d window, so titles appear within
  an hour of deploy+config).
