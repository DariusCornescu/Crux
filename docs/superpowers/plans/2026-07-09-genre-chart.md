# Genre Chart on SIGNALS — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** LLM-infer a fine-grained sub-genre per listened track (stored on the existing `ListeningSession.genre` column), aggregate the last 30 tracks into a genre distribution on `/signals/detail`, and draw a house-style horizontal bar chart on the SIGNALS screen. No migration.

**Architecture:** `app/genres.py::infer_pending` mirrors the mood/quote LLM pattern (one batched `llm.complete` call, offline-safe). Hooked into Spotify sync + a `POST /integrations/spotify/genres` backfill. `/signals/detail` counts genres over the last 30 tracks. Android adds a `GenreBars` Canvas/rect component to SIGNALS.

**Spec:** `docs/superpowers/specs/2026-07-09-genre-chart-design.md`
**Branch:** `feat/genre-chart` (worktree `C:/Users/dariu/Documents/GithubRepos/Splitrail/.worktrees/genre-chart`).
**Backend tests:** CWD `<worktree>/backend-fastapi`, interpreter `& "C:/Users/dariu/Documents/GithubRepos/Splitrail/.worktrees/rebrand-crux/backend-fastapi/.venv/Scripts/python.exe" -m pytest -q`. Baseline: **102 passed**.
**Android build:** CWD `<worktree>/android-native`, `.\gradlew.bat assembleDebug`.

---

### Task 1: Genre inference + aggregation (backend)

**Files:** Create `app/genres.py`, `tests/test_genres.py`. Modify `app/spotify.py` (sync hook), `app/routers/integrations.py` (backfill endpoint), `app/schemas.py` (GenreCount + SignalsOut), `app/routers/signals.py` (aggregate).

- [ ] **Step 1: Failing tests** — `tests/test_genres.py`:
```python
"""LLM-inferred genre per track + genre aggregation on /signals/detail."""
from datetime import datetime, timedelta, timezone

from app import genres
from app.models import ListeningSession


def _tracks(db, names):
    now = datetime.now(timezone.utc)
    for i, n in enumerate(names):
        db.add(ListeningSession(played_at=now - timedelta(hours=i + 1),
                                track_name=n, artist="A"))
    db.commit()


def test_infer_pending_offline_noop(db):
    _tracks(db, ["X", "Y"])                 # llm not configured in tests
    assert genres.infer_pending(db) == 0
    assert all(r.genre is None for r in db.query(ListeningSession).all())


def test_infer_pending_llm(db, monkeypatch):
    _tracks(db, ["Song A", "Song B"])
    monkeypatch.setattr(genres.llm, "is_configured", lambda: True)
    monkeypatch.setattr(genres.llm, "complete", lambda **k: "1. trap\n2. cloud rap\n")
    assert genres.infer_pending(db) == 2
    got = {r.track_name: r.genre for r in db.query(ListeningSession).all()}
    assert got == {"Song A": "trap", "Song B": "cloud rap"}
    assert genres.infer_pending(db) == 0    # idempotent — no NULL rows left


def test_signals_detail_genres(client, db):
    for n, g in [("A", "trap"), ("B", "trap"), ("C", "phonk")]:
        db.add(ListeningSession(played_at=datetime.now(timezone.utc), track_name=n, genre=g))
    db.commit()
    body = client.get("/signals/detail").json()
    counts = {row["genre"]: row["count"] for row in body["genres"]}
    assert counts == {"trap": 2, "phonk": 1}
    assert body["genres"][0]["genre"] == "trap"   # sorted desc


def test_backfill_genres_endpoint(client, db, monkeypatch):
    _tracks(db, ["Song A"])
    monkeypatch.setattr(genres.llm, "is_configured", lambda: True)
    monkeypatch.setattr(genres.llm, "complete", lambda **k: "1. phonk")
    r = client.post("/integrations/spotify/genres")
    assert r.status_code == 200 and r.json()["synced"] == 1
```
NOTE: the seed rows in `test_signals_detail_genres` use the same timestamp — that's
fine, `/signals/detail` orders by `played_at desc` and takes 30; all 3 are within.

- [ ] **Step 2: Run → FAIL** (no module/route/field).

- [ ] **Step 3: `app/genres.py`:**
```python
"""LLM-inferred fine-grained genre per listened track, stored on
ListeningSession.genre. Spotify removed its artist-genre endpoint (Feb 2026), so
— like the mood phrase — genre is inferred from track + artist by the LLM."""
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import llm
from app.models import ListeningSession

logger = logging.getLogger(__name__)

BATCH = 50
_LINE = re.compile(r"^\s*(\d+)\s*[.):\-]?\s*(.+?)\s*$")

SYSTEM = """You label music tracks with their specific sub-genre. For each
numbered "track — artist" line, reply with ONE line "N. genre" in the SAME
numbering, where genre is the specific sub-genre in at most 2 words, lowercase
(e.g. trap, cloud rap, phonk, drum and bass, indie rock, synthwave). Output only
those numbered lines, nothing else."""


def infer_pending(db: Session, limit: int = BATCH) -> int:
    """Fill ListeningSession.genre for rows lacking it, via one LLM call.
    Idempotent (touches only genre IS NULL); returns rows updated; 0 offline."""
    rows = list(db.scalars(
        select(ListeningSession)
        .where(ListeningSession.genre.is_(None))
        .order_by(ListeningSession.id)
        .limit(limit)
    ).all())
    if not rows or not llm.is_configured():
        return 0
    listing = "\n".join(f"{i + 1}. {r.track_name} — {r.artist or 'unknown'}"
                        for i, r in enumerate(rows))
    try:
        reply = llm.complete(system=SYSTEM,
                             messages=[{"role": "user", "content": listing}],
                             max_tokens=400)
    except Exception as e:
        logger.warning("genre inference failed: %s", e)
        return 0
    updated = 0
    for line in reply.splitlines():
        m = _LINE.match(line)
        if not m:
            continue
        idx = int(m.group(1)) - 1
        genre = m.group(2).strip().strip('"').lower()[:128]
        if 0 <= idx < len(rows) and genre and rows[idx].genre is None:
            rows[idx].genre = genre
            updated += 1
    db.commit()
    return updated
```

- [ ] **Step 4: Sync hook.** In `app/spotify.py`, add `from app import genres` near the top imports; in `sync_recently_played`, right after `aggregate_daily_mood(db)` (before the `logger.info`/return):
```python
    try:
        genres.infer_pending(db)
    except Exception as e:  # never let genre labelling break a sync
        logger.warning("genre inference skipped: %s", e)
```

- [ ] **Step 5: Backfill endpoint.** In `app/routers/integrations.py`, add `genres` to the `from app import ...` line, and after `spotify_backfill`:
```python
@router.post("/spotify/genres", response_model=SyncResult)
def spotify_genres(db: Session = Depends(get_db)):
    return SyncResult(synced=genres.infer_pending(db))
```

- [ ] **Step 6: Aggregation.** In `app/schemas.py` add:
```python
class GenreCount(BaseModel):
    genre: str
    count: int
```
and `genres: list[GenreCount] = []` to `SignalsOut`. In `app/routers/signals.py`: `from collections import Counter`, import `GenreCount`, and in `detail` (using the already-fetched last-30 `tracks`):
```python
    genre_counts = Counter(t.genre for t in tracks if t.genre)
```
then add `genres=[GenreCount(genre=g, count=c) for g, c in genre_counts.most_common()]` to the `SignalsOut(...)`.

- [ ] **Step 7: Run** `pytest tests/test_genres.py tests/test_signals.py -q` → PASS; full suite → **106 passed** (102 + 4 new).

- [ ] **Step 8: Commit** `feat: LLM-inferred track genres + genre distribution on /signals/detail`

---

### Task 2: GENRES bar chart (Android)

**Files:** Modify `network/DTOs.kt`, `ui/screens/SignalsScreen.kt`. Create `ui/components/GenreBars.kt`.
READ FIRST: `ui/components/ReportCharts.kt` (Canvas + Steel/Ink/Hairline idiom), `ui/screens/SignalsScreen.kt`, `network/DTOs.kt` (SignalsDTO), `ui/theme/Color.kt`.

- [ ] **Step 1: DTOs.** In `DTOs.kt`: `data class GenreCountDTO(val genre: String, val count: Int)`; add `val genres: List<GenreCountDTO> = emptyList()` to `SignalsDTO`.

- [ ] **Step 2: `ui/components/GenreBars.kt`** — horizontal bars, house style (imports mirror ReportCharts: Steel, Ink, Graphite, GateRed):
```kotlin
@Composable
fun GenreBars(genres: List<GenreCountDTO>, modifier: Modifier = Modifier) {
    Column(modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 18.dp)) {
        Text("GENRES — LAST 30", style = MaterialTheme.typography.labelSmall.copy(color = GateRed))
        Spacer(Modifier.height(10.dp))
        if (genres.isEmpty()) {
            Text("NO GENRES YET", style = MaterialTheme.typography.labelSmall.copy(color = Graphite))
            return@Column
        }
        val max = genres.maxOf { it.count }.coerceAtLeast(1)
        genres.forEach { g ->
            Row(Modifier.fillMaxWidth().padding(vertical = 3.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(
                    g.genre,
                    style = MaterialTheme.typography.bodyMedium.copy(color = Ink),
                    maxLines = 1,
                    modifier = Modifier.width(120.dp),
                )
                Box(Modifier.weight(1f).height(10.dp)) {
                    Box(Modifier.fillMaxWidth(g.count.toFloat() / max).fillMaxHeight().background(Steel))
                }
                Spacer(Modifier.width(8.dp))
                Text(
                    g.count.toString(),
                    style = MaterialTheme.typography.labelMedium.copy(color = Graphite),
                )
            }
        }
    }
}
```
(Add the needed imports: `background`, `Box`, `width`, `Alignment`, the `Steel`/`Ink`/`Graphite`/`GateRed` theme colors, `GenreCountDTO`. Follow ReportCharts.kt for exact import paths.)

- [ ] **Step 3: Render in SIGNALS.** In `ui/screens/SignalsScreen.kt`, in the `uiState.data != null` branch, between `ListeningSection(...)` and the `HairlineRule()` + `ConditionsSection(...)`, add (only when non-empty):
```kotlin
                if (data.genres.isNotEmpty()) {
                    HairlineRule()
                    GenreBars(data.genres)
                }
```
(import `com.darius.crux.ui.components.GenreBars`.)

- [ ] **Step 4: Build** `.\gradlew.bat assembleDebug` → BUILD SUCCESSFUL. **Commit** `feat(android): GENRES bar chart on the SIGNALS screen`

---

### Task 3: Verify + rollout
- [ ] Backend suite → 106 passed; `assembleDebug` → BUILD SUCCESSFUL.
- [ ] (Post-merge, manual) droplet pull + compose up; `curl -X POST https://api.crux.com.im/integrations/spotify/genres` once (backfill existing tracks); `curl https://api.crux.com.im/signals/detail` → `genres` populated; rebuild APK, adb install; on phone: SIGNALS shows the GENRES bars.

## Verification summary
T1 → genre tests green (106). T2 → assembleDebug. T3 → suite + build + backfill + phone.
