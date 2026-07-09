# Design: Genre chart on SIGNALS (LLM-inferred, fine-grained, last 30)

Date: 2026-07-09. Approved by Darius (AskUserQuestion): fine-grained sub-genres ·
last 30 tracks · on the SIGNALS screen.

## Summary

Show the distribution of music sub-genres across the last 30 listened tracks as
a house-style horizontal bar chart on SIGNALS. Spotify removed the artist-genre
endpoint (Feb 2026), so — like the mood phrase — the genre is **LLM-inferred**
from each track + artist and stored on the existing (currently unused)
`ListeningSession.genre` column. No migration (the column already exists).

## Scope

### A. Genre inference (backend)
- New `app/genres.py::infer_pending(db, limit=50) -> int`: select
  `ListeningSession` rows with `genre IS NULL` (ordered by id, capped), and if
  the LLM is configured, send their numbered `track — artist` list in one
  `llm.complete` call asking for a fine-grained sub-genre per line (≤2 words,
  lowercase). Parse `N. genre` lines by number, store on the rows' `genre`,
  commit, return count. Offline / LLM error / no pending rows → return 0 (genre
  stays NULL). Idempotent — only touches NULL rows, converges over syncs.
- Hook into `app/spotify.py::sync_recently_played`: after `aggregate_daily_mood`,
  call `genres.infer_pending(db)` in a guard so it never breaks a sync (runs in
  the background worker — no user latency). New tracks get a genre each sync.
- Backfill endpoint `POST /integrations/spotify/genres` →
  `SyncResult(synced=genres.infer_pending(db))`, run once for the existing ~30.

### B. Genre aggregation (backend)
- `app/schemas.py`: `class GenreCount(BaseModel): genre: str; count: int`; add
  `genres: list[GenreCount] = []` to `SignalsOut`.
- `app/routers/signals.py`: from the already-fetched last-30 `tracks`, count
  non-null `genre` with `collections.Counter`, emit `most_common()` as
  `GenreCount`s in the response.

### C. Genre chart (Android)
- DTO: `GenreCountDTO(genre, count)`; add `genres: List<GenreCountDTO> =
  emptyList()` to `SignalsDTO`.
- New `ui/components/GenreBars.kt`: a `GENRES — LAST 30` section (engraved
  GateRed label) with one horizontal bar per genre — genre label (Ink), a Steel
  bar whose width ∝ count/maxCount, and the count (Graphite). Empty → a single
  "NO GENRES YET" line. House style: filled rects, hairlines, no cards.
- Render in `SignalsScreen` between the LISTENING list and the CONDITIONS table
  (with a `HairlineRule`), only when `genres` is non-empty.

## Out of scope
- A migration (the `genre` column already exists).
- Real Spotify/third-party genre APIs (endpoint removed; LLM inference chosen).
- Per-artist caching beyond the per-track `genre` column.
- Time-window genre charts (chose last-30-tracks).

## Data flow
Spotify sync / backfill → `genres.infer_pending` (LLM) → `ListeningSession.genre`
→ `/signals/detail` counts the last 30 → Android `GenreBars` on SIGNALS.

## Testing (TDD)
- `tests/test_genres.py`: `infer_pending` with `llm` mocked (numbered reply →
  genres land on rows in order); no-LLM → returns 0, genres stay NULL;
  idempotent (2nd call 0). `/signals/detail` `genres` aggregation (seed genres →
  sorted counts). Backfill endpoint returns the count.
- Android: `assembleDebug` BUILD SUCCESSFUL.

## Rollout
Merge → droplet pull + compose up → `curl -X POST
https://api.crux.com.im/integrations/spotify/genres` once (backfill existing) →
verify `/signals/detail` `genres` is populated → rebuild APK, adb install →
GENRES bars show on SIGNALS.

## Risks
- LLM mislabels an obscure track → a slightly off genre; low stakes, correctable
  by re-null + re-infer if ever wanted.
- Batch numbering drift (LLM reorders/skips lines) → mitigated by parsing the
  explicit `N.` number, not position, and bounds-checking the index.
