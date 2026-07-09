# Design: Music mood as words + quote to the top

Date: 2026-07-09. Approved by Darius (AskUserQuestion): current mood only ·
fully words (drop the numeric mood readout + graph) · quote moves to the top.

## Summary

Replace the numeric music-mood readout (`MOOD ▲0.48`) with an LLM-derived
qualitative **mood phrase** (≤3 words, e.g. "low and restless", "locked-in
focus") produced by sentiment-reading the athlete's recent listening. The
numeric `valence` pipeline stays as the *input* signal; the phrase is what's
displayed. Also move the daily motivational quote from the bottom of the
Dashboard to the top.

Works even for the ~⅔ of tracks ReccoBeats can't score, because the LLM reads
song + artist names too.

## Scope

### A. Mood phrase backend (mirrors the daily-quote pattern)
- New model `app/models.py::DailyMood`: `id`, `day` (Date, unique, indexed),
  `phrase` (String(64)), `source` (String(8), "llm" | "fallback"). + migration.
- New `app/mood.py`:
  - `RECENT_DAYS = 2`.
  - `get_current(db) -> DailyMood`: return today's cached row if present; else
    read the last `RECENT_DAYS` of `ListeningSession` (name, artist, valence,
    energy). If `llm.is_configured()`: prompt for a ≤3-word lowercase mood
    phrase from the tracks; on success `source="llm"`. On no-LLM or any
    exception: deterministic fallback from average valence
    (≥0.6 "bright", ≥0.4 "even", <0.4 "heavy"; tracks-but-no-valence "even";
    no recent tracks "quiet"), `source="fallback"`. Cache the row, return it.
    One LLM call/day max (cached like the quote — the phrase is a daily read;
    recomputes next day).
- New router `app/routers/mood.py`: `GET /mood/current` → `{day, phrase, source}`.
- `app/routers/signals.py`: add `current_mood: str | None` to the `/signals/detail`
  payload via `mood.get_current(db).phrase` (shares the same daily cache; the
  dashboard's `/mood/current` and SIGNALS' `/signals/detail` both generate-or-read
  the one cached row).

### B. Dashboard (Android)
- COND strip: show `MOOD <phrase>` (lazy-loaded from `/mood/current`, like the
  quote) instead of `MOOD ▲<valence>`. `…` while loading, `--` if it fails.
- Remove the 14-day **MoodTrace** graph and its render block (kept in the DTO,
  just no longer drawn). The COND strip stays tappable → SIGNALS.
- Move the **quote to the top**: render it as an engraved line directly under
  the `CRUX` bezel header; remove the bottom quote block.
- `DashboardViewModel` gains a `mood: StateFlow<String?>` loaded independently
  (same lazy pattern as `quote`/`agenda`).

### C. SIGNALS screen (Android)
- Add a prominent current-mood headline near the top (`MOOD — <phrase>`), from
  the new `current_mood` field in `/signals/detail`.
- Drop the numeric **MOOD** column from the CONDITIONS 14-day table (DAY /
  SLEEP / RHR only). Per-track `▲valence` in the LISTENING list stays — that's
  the song's own property, not a mood readout.

## Out of scope
- Per-day mood-word history (chosen "current only").
- Intraday mood refresh (daily cache; recomputes next calendar day).
- Removing `mood_valence`/`mood_trend` from API payloads (harmless; still the
  input signal + used by weekly reports).

## Data flow
ReccoBeats valence/energy on `ListeningSession` → `app/mood.py` reads last 2
days + asks the LLM → `DailyMood.phrase` (cached) → `/mood/current` (dashboard
COND) and `/signals/detail.current_mood` (SIGNALS headline).

## Testing (TDD)
- `tests/test_mood.py`: fallback buckets (bright/even/heavy) from seeded
  valence; "quiet" with no recent tracks; cached per day (2nd call same row, no
  dup); LLM path mocked → phrase relayed, stripped, lowercased; `/mood/current`
  shape; `/signals/detail` carries `current_mood`.
- `tests/test_migrations.py` drift-guard stays green.
- Android: `assembleDebug` BUILD SUCCESSFUL.

## Rollout
Merge → droplet pull + compose up (migration auto-runs) → verify `/mood/current`
returns a phrase; rebuild APK; adb install; on phone: COND shows a mood word,
quote at the top, MoodTrace gone, SIGNALS shows the mood headline + 3-column
conditions table.

## Risks
- LLM returns a long/odd phrase → stored as-is; `String(64)` truncation guard
  in code (`phrase[:64]`), UI wraps. Low impact.
- First `/mood/current` or `/signals/detail` of the day pays one LLM latency
  (~1-3s); cached after. Lazy-loaded, never blocks the dashboard.
