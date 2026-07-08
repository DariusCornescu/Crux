# Dashboard v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the GATE instrument; add AGENDA (next 2 calendar events with titles), a data-aware LLM daily quote, and a tappable SIGNALS detail screen (songs + sleep).

**Architecture:** Three small backend additions (calendar `subject` column + `/calendar/upcoming`; `daily_quotes` table + `/quote/today` via `app/llm.py` with static fallback; `/signals/detail` read-only aggregation) followed by Android changes (drop GATE, add lazily-loaded AGENDA + QUOTE blocks, new SIGNALS route). Backend TDD with pytest; Android gated by `assembleDebug`.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest; Kotlin, Jetpack Compose, Retrofit.

**Spec:** `docs/superpowers/specs/2026-07-08-dashboard-v2-design.md`
**Branch:** `feat/dashboard-v2` (worktree `C:/Users/dariu/Documents/GithubRepos/Splitrail/.worktrees/dashboard-v2`).
**Backend tests:** CWD `<worktree>/backend-fastapi`, interpreter `& "C:/Users/dariu/Documents/GithubRepos/Splitrail/.worktrees/rebrand-crux/backend-fastapi/.venv/Scripts/python.exe" -m pytest -q`. Baseline: **83 passed**.
**Android build:** CWD `<worktree>/android-native`, `.\gradlew.bat assembleDebug`.

---

### Task 1: Calendar subject + `GET /calendar/upcoming`

**Files:**
- Modify: `backend-fastapi/app/models.py` (CalendarEvent), `app/calendar_sync.py::parse_ics`, `app/schemas.py`, `app/main.py` (router registration)
- Create: `backend-fastapi/app/routers/calendar.py`, `alembic/versions/<generated>_calendar_event_subject.py`
- Test: `backend-fastapi/tests/test_calendar_sync.py`

- [x] **Step 1: Failing tests** — append to `tests/test_calendar_sync.py` (it already has an `ICS` fixture with SUMMARY lines like "Sprint planning" and a `configured` fixture that monkeypatches settings + httpx; reuse its patterns — read the file first):

```python
def test_sync_stores_subject(db, configured):
    calendar_sync.sync_ics(db)
    subjects = {e.subject for e in db.query(CalendarEvent).all()}
    assert "Sprint planning" in subjects and "Design review" in subjects


def test_upcoming_endpoint_returns_future_events_in_order(client, db, configured):
    calendar_sync.sync_ics(db)
    r = client.get("/calendar/upcoming?limit=2")
    assert r.status_code == 200
    events = r.json()
    assert len(events) <= 2
    starts = [e["start"] for e in events]
    assert starts == sorted(starts)
    for e in events:
        assert set(e) >= {"start", "end", "subject", "attendee_count", "is_recurring"}
```

NOTE: the ICS fixture's events are dated June 2026 (mostly past). The weekly RRULE
(COUNT=3 from 2026-06-23) may or may not yield future occurrences relative to
today — if `events` is empty the ordering/shape assertions must still hold
(len<=2 over an empty list passes). To guarantee at least one future event,
add a VEVENT to the ICS string with DTSTART tomorrow — do this deterministically
by appending a second ICS constant `ICS_FUTURE` built with
`(datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y%m%dT090000Z")`
and a `configured_future` fixture, then assert `len(events) >= 1` with that.
Follow the file's existing fixture style.

- [x] **Step 2: Run → FAIL** (no `subject` attribute / 404 on /calendar/upcoming).

- [x] **Step 3: Model + migration.** In `app/models.py::CalendarEvent` after `subject_hash`:
```python
    subject: Mapped[str | None] = mapped_column(String(256), nullable=True)
```
Migration via `python -m alembic revision -m "calendar event subject"`:
```python
def upgrade() -> None:
    op.add_column("calendar_events", sa.Column("subject", sa.String(length=256), nullable=True))

def downgrade() -> None:
    op.drop_column("calendar_events", "subject")
```

- [x] **Step 4: parse_ics.** In `app/calendar_sync.py::parse_ics`, in the events.append dict, add:
```python
            "subject": str(component.get("SUMMARY", "")) or None,
```
(The upsert loop in `sync_ics` uses `**data` / setattr over dict keys — no other change.)

- [x] **Step 5: Schema + router.** In `app/schemas.py`:
```python
class UpcomingEvent(BaseModel):
    start: datetime
    end: datetime
    subject: str | None = None
    attendee_count: int | None = None
    is_recurring: bool = False
```
(add `datetime` to the existing `from datetime import date` import if missing).
Create `app/routers/calendar.py`:
```python
"""Upcoming work-calendar events for the Dashboard AGENDA block."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CalendarEvent
from app.schemas import UpcomingEvent

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/upcoming", response_model=list[UpcomingEvent])
def upcoming(limit: int = Query(2, ge=1, le=10), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(CalendarEvent)
        .where(CalendarEvent.start >= datetime.now(timezone.utc))
        .order_by(CalendarEvent.start)
        .limit(limit)
    ).all()
    return [UpcomingEvent(start=r.start, end=r.end, subject=r.subject,
                          attendee_count=r.attendee_count, is_recurring=r.is_recurring)
            for r in rows]
```
Register in `app/main.py`: add `calendar` to the `from app.routers import (...)` list and `app.include_router(calendar.router)` beside the others (module name `calendar` shadows the stdlib inside `app.routers` only — safe as a submodule import, but import it as `from app.routers import calendar as calendar_router` if the plain name collides; verify by running the suite).

- [x] **Step 6: Run** `pytest tests/test_calendar_sync.py tests/test_migrations.py -q` → PASS; full suite → 85 passed.

- [x] **Step 7: Commit** `feat: calendar events store subjects; GET /calendar/upcoming for the AGENDA block`

---

### Task 2: Daily quote

**Files:**
- Modify: `backend-fastapi/app/models.py`, `app/main.py`
- Create: `app/quotes.py`, `app/routers/quote.py`, `alembic/versions/<generated>_daily_quotes.py`
- Test: create `backend-fastapi/tests/test_quote.py`

- [x] **Step 1: Failing tests** — `tests/test_quote.py`:
```python
"""Daily quote: static fallback offline, cached per day, endpoint shape."""
from app import quotes
from app.models import DailyQuote


def test_quote_today_static_fallback_and_cached(db):
    q1 = quotes.get_today(db)          # llm not configured in tests -> static
    assert q1.source == "static" and q1.text
    q2 = quotes.get_today(db)
    assert q2.id == q1.id              # cached, no duplicate row
    assert db.query(DailyQuote).count() == 1


def test_quote_endpoint(client):
    r = client.get("/quote/today")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"day", "text", "source"}
    assert body["text"]
```

- [x] **Step 2: Run → FAIL** (no module/model).

- [x] **Step 3: Model + migration.** `app/models.py`:
```python
class DailyQuote(Base):
    __tablename__ = "daily_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True, index=True)
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(8), default="static")  # llm | static
```
Migration (`python -m alembic revision -m "daily quotes"`):
```python
def upgrade() -> None:
    op.create_table(
        "daily_quotes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=8), nullable=False),
    )
    op.create_index("ix_daily_quotes_day", "daily_quotes", ["day"], unique=True)

def downgrade() -> None:
    op.drop_index("ix_daily_quotes_day", table_name="daily_quotes")
    op.drop_table("daily_quotes")
```
Run the drift-guard after — if it complains about nullable/server_default details, match the model exactly.

- [x] **Step 4: `app/quotes.py`:**
```python
"""Daily motivational line — LLM-personalized from the week's training, cached
per day in daily_quotes, deterministic static fallback offline."""
import logging
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import llm
from app.models import Activity, DailyQuote, EffortMode

logger = logging.getLogger(__name__)

STATIC_QUOTES = [
    "The mountain doesn't care how you feel. Show up anyway.",
    "Base miles are deposits. Race day makes the withdrawal.",
    "Slow is smooth, smooth is far.",
    "You don't rise to the summit; you fall to your training.",
    "Heavy pack, light mind.",
    "Consistency beats intensity when intensity quits.",
    "Every easy kilometer is a brick in the engine.",
    "The best pace is the one you can hold tomorrow too.",
    "Vertical meters are honest meters.",
    "Train the engine, respect the springs.",
    "No wind is unfair if you packed for it.",
    "Today's discipline is next season's freedom.",
]

SYSTEM = """Write ONE short motivational line (max 120 characters) for an athlete
rebuilding aerobic base and preparing for mountaineering. Reference the training
numbers given if useful. No quotes around it, no emoji, no hashtags. Dry,
timing-sheet tone — not cheerleading."""


def _week_snapshot(db: Session) -> str:
    today = date.today()
    week_start = datetime.combine(today - timedelta(days=today.weekday()),
                                  time.min, tzinfo=timezone.utc)
    activities = db.scalars(select(Activity).where(Activity.start_time >= week_start)).all()
    km = sum((a.distance_m or 0) / 1000 for a in activities if a.mode == EffortMode.aerobic)
    vert = sum(a.elevation_gain_m or 0 for a in activities if a.mode == EffortMode.loaded)
    return (f"This week so far: {len(activities)} sessions, {km:.1f} km aerobic, "
            f"{int(vert)} m vertical under load.")


def get_today(db: Session) -> DailyQuote:
    today = date.today()
    row = db.scalar(select(DailyQuote).where(DailyQuote.day == today))
    if row is not None:
        return row
    text, source = None, "static"
    if llm.is_configured():
        try:
            text = llm.complete(system=SYSTEM,
                                messages=[{"role": "user", "content": _week_snapshot(db)}],
                                max_tokens=80).strip().strip('"')
            source = "llm"
        except Exception as e:
            logger.warning("quote generation failed, using static: %s", e)
            text = None
    if not text:
        text, source = STATIC_QUOTES[today.timetuple().tm_yday % len(STATIC_QUOTES)], "static"
    row = DailyQuote(day=today, text=text, source=source)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
```

- [x] **Step 5: Router** `app/routers/quote.py`:
```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date

from app import quotes
from app.database import get_db

router = APIRouter(prefix="/quote", tags=["quote"])


class QuoteOut(BaseModel):
    day: date
    text: str
    source: str


@router.get("/today", response_model=QuoteOut)
def today(db: Session = Depends(get_db)):
    row = quotes.get_today(db)
    return QuoteOut(day=row.day, text=row.text, source=row.source)
```
Register in `app/main.py` like the others.

- [x] **Step 6: Run** `pytest tests/test_quote.py tests/test_migrations.py -q` → PASS; full suite → 87 passed.

- [x] **Step 7: Commit** `feat: daily data-aware quote (LLM + static fallback), GET /quote/today`

---

### Task 3: `GET /signals/detail`

**Files:**
- Create: `backend-fastapi/app/routers/signals.py`; Modify: `app/schemas.py`, `app/main.py`
- Test: create `backend-fastapi/tests/test_signals.py`

- [x] **Step 1: Failing test** — `tests/test_signals.py`:
```python
from datetime import datetime, timedelta, timezone

from app.models import DailySummary, ListeningSession


def test_signals_detail_shape_and_order(client, db):
    now = datetime.now(timezone.utc)
    db.add_all([
        ListeningSession(played_at=now - timedelta(hours=2), track_name="Older", valence=0.4),
        ListeningSession(played_at=now, track_name="Newest", artist="A", valence=0.8, energy=0.9),
    ])
    db.add(DailySummary(day=now.date(), sleep_duration_min=432, resting_hr=52, mood_valence=0.5))
    db.commit()

    r = client.get("/signals/detail")
    assert r.status_code == 200
    body = r.json()
    tracks = body["recent_tracks"]
    assert [t["track"] for t in tracks] == ["Newest", "Older"]
    assert set(tracks[0]) >= {"played_at", "track", "artist", "valence", "energy"}
    daily = body["daily"]
    assert daily[0]["sleep_min"] == 432 and daily[0]["resting_hr"] == 52
```

- [x] **Step 2: Run → FAIL** (404).

- [x] **Step 3: Schemas** (`app/schemas.py`):
```python
class SignalTrack(BaseModel):
    played_at: datetime
    track: str
    artist: str | None = None
    valence: float | None = None
    energy: float | None = None


class SignalDay(BaseModel):
    day: date
    sleep_min: int | None = None
    sleep_score: float | None = None
    resting_hr: int | None = None
    mood_valence: float | None = None
    mood_energy: float | None = None


class SignalsOut(BaseModel):
    recent_tracks: list[SignalTrack]
    daily: list[SignalDay]
```

- [x] **Step 4: Router** `app/routers/signals.py`:
```python
"""Detail payload behind the Dashboard's tappable COND/MoodTrace region."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailySummary, ListeningSession
from app.schemas import SignalDay, SignalsOut, SignalTrack

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/detail", response_model=SignalsOut)
def detail(db: Session = Depends(get_db)):
    tracks = db.scalars(select(ListeningSession)
                        .order_by(ListeningSession.played_at.desc()).limit(30)).all()
    days = db.scalars(select(DailySummary)
                      .order_by(DailySummary.day.desc()).limit(14)).all()
    return SignalsOut(
        recent_tracks=[SignalTrack(played_at=t.played_at, track=t.track_name, artist=t.artist,
                                   valence=t.valence, energy=t.energy) for t in tracks],
        daily=[SignalDay(day=d.day, sleep_min=d.sleep_duration_min, sleep_score=d.sleep_score,
                         resting_hr=d.resting_hr, mood_valence=d.mood_valence,
                         mood_energy=d.mood_energy) for d in days],
    )
```
Register in `app/main.py`.

- [x] **Step 5: Run** full suite → 88 passed (plan baseline); actual 90 passed including the
Task 2 code-review ride-along (`test_quote_llm_branch_and_failure_fallback`,
`test_quote_llm_failure_falls_back_static` added to `tests/test_quote.py`: 87 + 1 signals
+ 2 quote ride-along = 90). **Commit** `feat: GET /signals/detail (recent tracks + 14-day conditions)`

---

### Task 4: Android — remove GATE, add AGENDA + QUOTE blocks

**Files (all under `android-native/app/src/main/java/com/darius/crux/`):**
- Modify: `ui/screens/DashboardScreen.kt`, `ui/components/Instruments.kt`, `util/Constants.kt`, `network/DTOs.kt`, `network/CruxApi.kt`, `data/repository/DashboardRepository.kt` (or a new small repo), `ui/viewmodel/DashboardViewModel.kt`
- READ FIRST for patterns: `network/CruxApi.kt`, `network/DTOs.kt`, `data/repository/ReportsRepository.kt`, `ui/viewmodel/DashboardViewModel.kt`, `ui/components/Panels.kt`

- [x] **Step 1: Remove GATE.** In `DashboardScreen.kt` delete `GateInstrument(data.gate)` + the `HairlineRule()` directly after it and the `GateInstrument` import. In `Instruments.kt` delete the `GateInstrument` composable + now-unused imports (keep `StripInstrument`/`AltiInstrument`). Delete `SPRINT_PB_SECONDS` from `util/Constants.kt` (delete the file only if it becomes empty and nothing imports it).

- [x] **Step 2: DTOs + API.** In `DTOs.kt` add:
```kotlin
data class UpcomingEventDto(
    val start: String, val end: String,
    val subject: String?, @SerializedName("attendee_count") val attendeeCount: Int?,
    @SerializedName("is_recurring") val isRecurring: Boolean,
)

data class QuoteDto(val day: String, val text: String, val source: String)
```
(match the file's existing serialization annotation style — read it first; if it uses Moshi/kotlinx instead of Gson, mirror that). In `CruxApi.kt`:
```kotlin
    @GET("calendar/upcoming")
    suspend fun upcomingEvents(@Query("limit") limit: Int = 2): List<UpcomingEventDto>

    @GET("quote/today")
    suspend fun quoteToday(): QuoteDto
```

- [x] **Step 3: ViewModel.** In `DashboardViewModel`, add two independent lazily-loaded state flows (`agenda: List<UpcomingEventDto>?`, `quote: String?`), each fetched in its own `viewModelScope.launch` with try/catch → null on failure (hidden UI). Follow the existing UiState/StateFlow pattern in the file; do NOT block or merge into the main dashboard load.

- [x] **Step 4: AGENDA UI.** In `DashboardScreen.kt`, where GATE used to render, add an `AgendaBlock(events, expandedIndex, onToggle)` composable (new, in `ui/components/Panels.kt` or inline in the screen file — follow where sibling small blocks live):
  - Hidden entirely when `events.isNullOrEmpty()`.
  - Engraved label "NEXT UP" (labelSmall, GateRed accent like "COND").
  - Per event a row: `HH:mm–HH:mm · <subject or "BUSY">` — time in Plex Mono (labelMedium), subject in bodyMedium; today's events get GateRed time, others Ink.
  - Tap toggles an expanded block under the row: weekday + date line, duration in minutes, `ATTENDEES <n>` when non-null. Hairline rules, no cards, 20dp margins — match the file's conventions.
  - Parse ISO datetimes with `java.time.OffsetDateTime.parse` and convert to the device zone.

- [x] **Step 5: QUOTE UI.** At the bottom of `DashboardBody` (after `AltiInstrument`), when `quote != null`: `HairlineRule()` then the quote text centered, `bodyMedium` in Graphite, 20dp horizontal padding, 12dp vertical.

- [x] **Step 6: Build** `.\gradlew.bat assembleDebug` → BUILD SUCCESSFUL. **Commit** `feat(android): AGENDA + daily quote on Dashboard; GATE removed`

---

### Task 5: Android — SIGNALS screen + tappable top region

**Files:**
- Create: `ui/screens/SignalsScreen.kt`, `ui/viewmodel/SignalsViewModel.kt`
- Modify: `network/DTOs.kt`, `network/CruxApi.kt`, `data/repository/` (new `SignalsRepository.kt` following `ReportsRepository` pattern), `ui/navigation/NavGraph.kt`, `ui/screens/DashboardScreen.kt`
- READ FIRST: `ui/navigation/NavGraph.kt` (how `reports/{id}` is pushed), `ui/screens/ReportDetailScreen.kt` (pushed-screen scaffold/back pattern)

- [x] **Step 1: DTOs + API.**
```kotlin
data class SignalTrackDto(@SerializedName("played_at") val playedAt: String, val track: String,
                          val artist: String?, val valence: Double?, val energy: Double?)
data class SignalDayDto(val day: String, @SerializedName("sleep_min") val sleepMin: Int?,
                        @SerializedName("sleep_score") val sleepScore: Double?,
                        @SerializedName("resting_hr") val restingHr: Int?,
                        @SerializedName("mood_valence") val moodValence: Double?,
                        @SerializedName("mood_energy") val moodEnergy: Double?)
data class SignalsDto(@SerializedName("recent_tracks") val recentTracks: List<SignalTrackDto>,
                      val daily: List<SignalDayDto>)
```
`CruxApi`: `@GET("signals/detail") suspend fun signalsDetail(): SignalsDto`

- [x] **Step 2: Repository + ViewModel** following the `ReportsRepository`/`ReportDetailViewModel` patterns (RepoResult, UiState with isLoading/error/data, load() on init).

- [x] **Step 3: SignalsScreen.** Timing-sheet style, vertical scroll:
  - Header row: "SIGNALS" titleSmall + a back affordance consistent with `ReportDetailScreen`.
  - Section `LISTENING — LAST 30`: per track one row `HH:mm  TITLE — ARTIST   ▲0.82` (mono time, sans title, mono valence right-aligned; `--` when valence null). Group by day with an engraved date row between days.
  - `HairlineRule()`, then section `CONDITIONS — 14 DAYS`: header row `DAY  SLEEP  RHR  MOOD` in labelSmall Graphite; one mono row per day (`7:12`-style sleep from minutes, `--` for nulls).
  - Loading/error via the existing `LoadingStrip`/`ErrorStrip` components.

- [x] **Step 4: Wire navigation.** In `NavGraph.kt` add `composable("signals") { SignalsScreen(onBack = { nav.popBackStack() }) }` beside the `reports/{id}` route. In `DashboardScreen.kt`, wrap the top region (`ConditionsStrip` + `MoodTrace` block) in a `Column(Modifier.clickable { onOpenSignals() })`; thread an `onOpenSignals: () -> Unit` parameter from the NavGraph the same way `ReportsScreen(onOpenReport=...)` is threaded.

- [x] **Step 5: Build** `.\gradlew.bat assembleDebug` → BUILD SUCCESSFUL. **Commit** `feat(android): SIGNALS detail screen behind the COND/MoodTrace region`

---

### Task 6: Full verification + rollout

- [x] **Step 1:** Backend full suite → 88 passed. Android `assembleDebug` → BUILD SUCCESSFUL.
- [ ] **Step 2 (manual, post-merge):** droplet `git pull` + compose up; user sets `CALENDAR_ICS_URL` in `/srv/crux/backend-fastapi/.env` (+ compose up again); verify `GET /quote/today` and `/calendar/upcoming`; build + `adb install -r` the APK; verify on phone: GATE gone, AGENDA (after ICS config), quote line, SIGNALS screen opens from the top region.

## Verification summary
1. T1 → calendar tests + drift-guard green (85).
2. T2 → quote tests green (87).
3. T3 → signals test green (88).
4. T4/T5 → `assembleDebug` BUILD SUCCESSFUL after each.
5. T6 → suite + build + on-phone verification.
