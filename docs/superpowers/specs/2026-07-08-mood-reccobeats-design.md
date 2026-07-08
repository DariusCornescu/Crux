# Design: Restore listening mood via ReccoBeats + enrich chat with recent tracks

Date: 2026-07-08

## Summary

Spotify deprecated its `/v1/audio-features` endpoint on 2024-11-27 for apps created
afterward; Crux's Spotify app receives `403`, so every `ListeningSession` is stored
with `valence`/`energy` = NULL and **all** mood-derived features are permanently
blank: the dashboard `MoodTrace` barograph (hidden when every day is null), the
`COND … MOOD` readout (`--`), and the audio-priming correlation.

This restores mood by sourcing the same metrics from **ReccoBeats** — a free,
no-auth API that accepts Spotify track IDs and returns Spotify-shaped audio
features (`valence`, `energy`, `tempo`, …). It additionally feeds the athlete's
recent tracks into the chat context so the chat can discuss listening
qualitatively even for tracks without a numeric valence.

Backend-only. No Android, dashboard, report, or scheduler changes — mood simply
starts flowing into what already exists.

## Root cause (verified in code)

- `app/spotify.py::_fetch_audio_features` calls Spotify's audio-features → `403`
  → returns `{}` → per-track `valence/energy` stay NULL.
- `app/spotify.py::aggregate_daily_mood` averages NULLs → `DailySummary.mood_valence`
  = NULL → `MoodTrace` hidden, `COND MOOD` `--`, `audio_priming` empty.
- `app/chat_service.py::build_context` never included the raw tracks — only the
  (NULL) numeric mood — so the chat has nothing to say about listening.

## Scope

### A. Swap audio-features source to ReccoBeats
- `app/config.py`: add `reccobeats_base_url: str = "https://api.reccobeats.com"`.
- `app/spotify.py`: `FEATURES_URL` → `f"{settings.reccobeats_base_url}/v1/audio-features"`.
- `_fetch_audio_features(track_ids)`:
  - No `Authorization` header (ReccoBeats needs none).
  - Send Spotify track IDs as `?ids=<comma-separated>`, **batched** (≤ 40 per call)
    with a ~0.5s gap between batches to avoid HTTP 429.
  - Parse the response `content[]` array into `{spotify_track_id: {valence, energy, tempo}}`.
  - Same graceful-degrade contract: non-200 / error → skip those tracks (valence
    stays NULL). Return shape unchanged, so all callers are untouched.

### B. Store the Spotify track id
- `app/models.py::ListeningSession`: add
  `spotify_track_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)`.
- New Alembic migration: `add_column("listening_sessions", "spotify_track_id", String(64), nullable=True)` + index; downgrade drops it.
- `app/spotify.py::sync_recently_played`: set `row.spotify_track_id = track.get("id")`
  (the id is currently fetched then discarded).

### C. Enrich chat context
- `app/chat_service.py::build_context`: add a `recent_listening` field — the last
  ~20 `ListeningSession` rows (by `played_at` desc) as
  `[{day, track, artist, valence, energy}]`. The `listening` rows are already
  queried in `build_context`; this serializes them into the snapshot.

### D. Backfill existing rows (approved)
- `app/spotify.py::backfill_audio_features(db)`: select `ListeningSession` rows
  where `spotify_track_id IS NOT NULL AND valence IS NULL`, re-fetch via ReccoBeats
  in batches, update rows, then call `aggregate_daily_mood`.
- Exposed as `POST /integrations/spotify/backfill` (idempotent) in
  `app/routers/integrations.py`; run once after deploy.

## Out of scope
- LLM-inferred numeric valence (deferred; the chat already gets the raw track list
  for qualitative reasoning, which is the immediately useful half).
- Genre enrichment.
- Any Android / dashboard / report / scheduler change.

## Data flow (after)
Spotify recently-played → `ListeningSession` (now carrying `spotify_track_id`) →
ReccoBeats audio-features → `valence/energy/tempo` on rows → `aggregate_daily_mood`
→ `DailySummary.mood_valence/energy` → dashboard `COND MOOD` + `MoodTrace` +
`audio_priming`; and `build_context` includes `recent_listening` for the chat.

## Testing (TDD — tests written first)
- `tests/test_spotify.py`: point the mock at `reccobeats_base_url` + the `content[]`
  response shape; assert `valence/energy/tempo` land on rows, `spotify_track_id` is
  stored, and daily aggregation populates `DailySummary`; cover the non-200
  graceful-degrade path; assert batching splits large id lists.
- `tests/test_chat.py`: assert `recent_listening` appears in `build_context` with
  the expected shape.
- Backfill: a null-valence row with `spotify_track_id` set gets populated after
  `backfill_audio_features`.
- `tests/test_migrations.py` drift-guard stays green (new column matched by the
  migration).

## Rollout
Merge to `main` → on the Droplet: `cd /srv/crux && git pull` →
`cd backend-fastapi && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
(migration auto-runs on API startup) → `curl -X POST https://api.crux.com.im/integrations/spotify/backfill`
once → verify `/dashboard/summary` `mood_trend` has non-null values and the chat
answers a "what have I been listening to?" question.

## Risks
- **ReccoBeats coverage/availability** (free third-party): tracks it lacks stay
  NULL (acceptable — degrades gracefully). If it becomes unreliable, the deferred
  LLM-inference path is the contingency.
- **Response-shape assumption**: sources confirm a `content[]` array but not
  exactly how each item echoes the queried Spotify id. Pin this down against a real
  (or captured) response during TDD; if items carry only a ReccoBeats id/href,
  map by request order or by an echoed id field.
- **Rate limiting (429)**: mitigated by batching + ~0.5s spacing; the fetch already
  degrades gracefully if a batch fails.
