# Music Mood as Words + Quote to Top — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the numeric music-mood readout with an LLM-derived ≤3-word mood phrase (cached daily, offline fallback); drop the numeric MoodTrace graph; move the daily quote to the top of the Dashboard; add a mood headline to SIGNALS.

**Architecture:** Backend mirrors the daily-quote pattern — a `DailyMood` table + `app/mood.py::get_current` (LLM or valence-bucket fallback, cached per day) + `GET /mood/current`, and `current_mood` added to `/signals/detail`. Android lazy-loads the phrase (like the quote), shows it in COND, removes the graph, moves the quote up, and adds a SIGNALS headline.

**Spec:** `docs/superpowers/specs/2026-07-09-mood-words-design.md`
**Branch:** `feat/mood-words` (worktree `C:/Users/dariu/Documents/GithubRepos/Splitrail/.worktrees/mood-words`).
**Backend tests:** CWD `<worktree>/backend-fastapi`, interpreter `& "C:/Users/dariu/Documents/GithubRepos/Splitrail/.worktrees/rebrand-crux/backend-fastapi/.venv/Scripts/python.exe" -m pytest -q`. Baseline: **96 passed**.
**Android build:** CWD `<worktree>/android-native`, `.\gradlew.bat assembleDebug`.

---

### Task 1: Mood phrase backend

**Files:** Modify `app/models.py`, `app/main.py`, `app/routers/signals.py`, `app/schemas.py` (SignalsOut). Create `app/mood.py`, `app/routers/mood.py`, `alembic/versions/<generated>_daily_moods.py`, `tests/test_mood.py`.

- [ ] **Step 1: Failing tests** — `tests/test_mood.py`:
```python
"""Music mood phrase: fallback buckets offline, cached per day, endpoint shape."""
from datetime import datetime, timedelta, timezone

from app import mood
from app.models import DailyMood, ListeningSession


def _add_tracks(db, valences):
    now = datetime.now(timezone.utc)
    for i, v in enumerate(valences):
        db.add(ListeningSession(played_at=now - timedelta(hours=i + 1),
                                track_name=f"T{i}", artist="A", valence=v))
    db.commit()


def test_fallback_buckets(db):
    _add_tracks(db, [0.8, 0.7])            # avg 0.75 -> bright
    m = mood.get_current(db)
    assert m.source == "fallback" and m.phrase == "bright"


def test_fallback_quiet_when_no_recent_listening(db):
    assert mood.get_current(db).phrase == "quiet"


def test_cached_per_day(db):
    _add_tracks(db, [0.1])                 # heavy
    m1 = mood.get_current(db)
    m2 = mood.get_current(db)
    assert m1.id == m2.id and db.query(DailyMood).count() == 1
    assert m1.phrase == "heavy"


def test_llm_phrase_relayed(db, monkeypatch):
    _add_tracks(db, [0.5])
    monkeypatch.setattr(mood.llm, "is_configured", lambda: True)
    monkeypatch.setattr(mood.llm, "complete", lambda **k: '  "Low And Restless" ')
    m = mood.get_current(db)
    assert m.source == "llm" and m.phrase == "low and restless"


def test_mood_endpoint(client):
    r = client.get("/mood/current")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"day", "phrase", "source"} and body["phrase"]


def test_signals_detail_carries_current_mood(client, db):
    _add_tracks(db, [0.9])
    body = client.get("/signals/detail").json()
    assert body["current_mood"] == "bright"
```

- [ ] **Step 2: Run → FAIL** (no module/model/route).

- [ ] **Step 3: Model + migration.** `app/models.py` (after `DailyQuote`):
```python
class DailyMood(Base):
    __tablename__ = "daily_moods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True, index=True)
    phrase: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(8), default="fallback")  # llm | fallback
```
Migration (`python -m alembic revision -m "daily moods"`):
```python
def upgrade() -> None:
    op.create_table(
        "daily_moods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("phrase", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=8), nullable=False),
    )
    op.create_index("ix_daily_moods_day", "daily_moods", ["day"], unique=True)

def downgrade() -> None:
    op.drop_index("ix_daily_moods_day", table_name="daily_moods")
    op.drop_table("daily_moods")
```
Run the drift-guard after; match the model if it flags anything.

- [ ] **Step 4: `app/mood.py`:**
```python
"""Current music mood as a short phrase — LLM sentiment of recent listening,
cached per day in daily_moods, deterministic valence-bucket fallback offline."""
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import llm
from app.models import DailyMood, ListeningSession

logger = logging.getLogger(__name__)

RECENT_DAYS = 2

SYSTEM = """You read an athlete's recent music listening and name the emotional
mood in AT MOST 3 words, lowercase (e.g. "low and restless", "locked-in focus",
"bright and loose"). Use the songs, artists, and any valence (0=negative..
1=positive) / energy (0=calm..1=intense) values given. Reply with ONLY the mood
phrase — no quotes, no punctuation at the ends, no explanation."""


def _recent(db: Session) -> list[ListeningSession]:
    since = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)
    return list(db.scalars(
        select(ListeningSession)
        .where(ListeningSession.played_at >= since)
        .order_by(ListeningSession.played_at.desc())
        .limit(40)
    ).all())


def _snapshot(tracks: list[ListeningSession]) -> str:
    lines = []
    for t in tracks:
        extra = ""
        if t.valence is not None:
            extra = f" (valence {t.valence:.2f}, energy {t.energy if t.energy is not None else '?'})"
        lines.append(f"- {t.track_name} — {t.artist or 'unknown'}{extra}")
    return "Recent listening (last 2 days):\n" + "\n".join(lines)


def _fallback(tracks: list[ListeningSession]) -> str:
    if not tracks:
        return "quiet"
    vals = [t.valence for t in tracks if t.valence is not None]
    if not vals:
        return "even"
    avg = sum(vals) / len(vals)
    if avg >= 0.6:
        return "bright"
    if avg >= 0.4:
        return "even"
    return "heavy"


def get_current(db: Session) -> DailyMood:
    today = date.today()
    row = db.scalar(select(DailyMood).where(DailyMood.day == today))
    if row is not None:
        return row
    tracks = _recent(db)
    phrase, source = None, "fallback"
    if tracks and llm.is_configured():
        try:
            phrase = llm.complete(system=SYSTEM,
                                  messages=[{"role": "user", "content": _snapshot(tracks)}],
                                  max_tokens=16).strip().strip('"').strip().lower()[:64]
            source = "llm"
        except Exception as e:
            logger.warning("mood generation failed, using fallback: %s", e)
            phrase = None
    if not phrase:
        phrase, source = _fallback(tracks), "fallback"
    row = DailyMood(day=today, phrase=phrase, source=source)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
```

- [ ] **Step 5: Router + registration.** `app/routers/mood.py`:
```python
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import mood
from app.database import get_db

router = APIRouter(prefix="/mood", tags=["mood"])


class MoodOut(BaseModel):
    day: date
    phrase: str
    source: str


@router.get("/current", response_model=MoodOut)
def current(db: Session = Depends(get_db)):
    row = mood.get_current(db)
    return MoodOut(day=row.day, phrase=row.phrase, source=row.source)
```
Register in `app/main.py` (grouped import + `app.include_router(mood.router)`).

- [ ] **Step 6: `/signals/detail` carries the mood.** In `app/schemas.py::SignalsOut` add `current_mood: str | None = None`. In `app/routers/signals.py`: `from app import mood` and set `current_mood=mood.get_current(db).phrase` in the returned `SignalsOut(...)`.

- [ ] **Step 7: Run** `pytest tests/test_mood.py tests/test_migrations.py tests/test_signals.py -q` → PASS; full suite → **102 passed** (96 + 6 new).

- [ ] **Step 8: Commit** `feat: music mood phrase (LLM sentiment + fallback), GET /mood/current, in /signals/detail`

---

### Task 2: Android — COND phrase, drop graph, quote to top

**Files (under `android-native/app/src/main/java/com/darius/crux/`):** Modify `network/DTOs.kt`, `network/CruxApi.kt`, `data/repository/DashboardRepository.kt`, `ui/viewmodel/DashboardViewModel.kt`, `ui/screens/DashboardScreen.kt`.
READ FIRST: `network/DTOs.kt` (QuoteDTO style), `ui/screens/DashboardScreen.kt`, `ui/viewmodel/DashboardViewModel.kt`.

- [ ] **Step 1: DTO + API.** In `DTOs.kt` (bare-field house style): `data class MoodDTO(val day: String, val phrase: String, val source: String)`. In `CruxApi.kt`: `@GET("mood/current") suspend fun getMoodCurrent(): Response<MoodDTO>`.

- [ ] **Step 2: Repository.** Add to `DashboardRepository` (mirror `getQuoteToday`):
```kotlin
    /** Current music mood phrase — independent of the main dashboard load. */
    suspend fun getMoodCurrent(): RepoResult<MoodDTO> = withContext(Dispatchers.IO) {
        try {
            val response = api.getMoodCurrent()
            if (response.isSuccessful && response.body() != null) {
                RepoResult.Success(response.body()!!)
            } else {
                Log.w(TAG, "Server error ${response.code()}")
                RepoResult.Error("SERVER ${response.code()}")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Network error: ${e.message}")
            RepoResult.Error("NO SIGNAL — ${e.message ?: "network error"}")
        }
    }
```
(import `com.darius.crux.network.MoodDTO`.)

- [ ] **Step 3: ViewModel.** In `DashboardViewModel` add a `mood` flow mirroring `quote`:
```kotlin
    private val _mood = MutableStateFlow<String?>(null)
    val mood: StateFlow<String?> = _mood.asStateFlow()
```
Add `loadMood()` (copy of `loadQuote()` → `result.data.phrase`) and call it in `load()` next to `loadAgenda()`/`loadQuote()`.

- [ ] **Step 4: DashboardScreen — collect mood, move quote to top, drop graph.**
  - Collect: `val mood by viewModel.mood.collectAsState()`.
  - After `BezelHeader(...)` in the outer Column, render the quote at the TOP:
```kotlin
        quote?.let {
            HairlineRule()
            Text(
                it,
                style = MaterialTheme.typography.bodyMedium.copy(color = Graphite, textAlign = TextAlign.Center),
                modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 12.dp),
            )
        }
```
  - In `DashboardBody`: remove the `quote: String?` param and the bottom quote block (the `if (quote != null) {...}` at the end). Change the `DashboardBody(...)` call to drop `quote =` and add `moodPhrase = mood`.
  - Remove the MoodTrace block (`if (data.moodTrend.any { it != null }) { MoodTrace(...) ... }`) and the `MoodTrace` import. Keep the `Column(Modifier.fillMaxWidth().clickable(onClick = onOpenSignals)) { ConditionsStrip(...) }` wrapper (now wrapping only the COND strip).
  - `ConditionsStrip(c: Conditions, moodPhrase: String?)`: change the mood cell from valence to the phrase:
```kotlin
    val mood = moodPhrase ?: "…"
    ...
    Text("SLEEP $sleep · RHR $rhr · MOOD $mood", style = MaterialTheme.typography.labelSmall)
```
  (drop the `c.moodValence` formatting line.)

- [ ] **Step 5: Build** `.\gradlew.bat assembleDebug` → BUILD SUCCESSFUL. **Commit** `feat(android): music mood phrase in COND, quote to the top, MoodTrace removed`

---

### Task 3: Android — SIGNALS mood headline + drop numeric MOOD column

**Files:** Modify `network/DTOs.kt` (SignalsDTO), `ui/screens/SignalsScreen.kt`.
READ FIRST: `ui/screens/SignalsScreen.kt`, `network/DTOs.kt` (SignalsDTO).

- [ ] **Step 1: DTO.** Add `current_mood: String?` (bare field, nullable) to `SignalsDTO` in `DTOs.kt`.

- [ ] **Step 2: SignalsScreen headline.** In the `uiState.data != null` branch, before `ListeningSection(...)`, render a mood headline when present:
```kotlin
                data.current_mood?.let { phrase ->
                    Column(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 18.dp)) {
                        Text("MOOD", style = MaterialTheme.typography.labelSmall.copy(color = GateRed))
                        Spacer(Modifier.height(6.dp))
                        Text(phrase, style = MaterialTheme.typography.titleSmall.copy(color = Ink))
                    }
                    HairlineRule()
                }
```

- [ ] **Step 3: Drop the numeric MOOD column** from `ConditionsSection`:
  - Header `Row`: remove the `MOOD` `Text`; keep DAY / SLEEP / RHR (three `weight(1f)` cells).
  - `DayRow`: remove the `mood` val and its `Text`; keep label / sleep / rhr (three cells).

- [ ] **Step 4: Build** → BUILD SUCCESSFUL. **Commit** `feat(android): SIGNALS mood headline; numeric MOOD column dropped`

---

### Task 4: Verify + rollout
- [ ] Backend suite → 102 passed; `assembleDebug` → BUILD SUCCESSFUL.
- [ ] (Post-merge, manual) droplet pull + compose up (migration auto-runs); `curl https://api.crux.com.im/mood/current` → a phrase; rebuild APK; adb install; on phone: COND shows a mood word, quote at the top, no MoodTrace graph, SIGNALS shows the mood headline and a 3-column conditions table.

## Verification summary
T1 → mood tests + drift-guard green (102). T2/T3 → assembleDebug after each. T4 → suite + build + phone.
