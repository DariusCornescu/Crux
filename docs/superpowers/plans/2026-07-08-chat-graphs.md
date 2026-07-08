# Chat v2 + Report Graphs + PB Purge — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** DELETE /chat/history + streaming SSE chat + GET /reports/{id}/metrics + purge the 6.91 PB everywhere; Android: CLEAR button, token-streaming chat UI, three report mini-charts.

**Architecture:** Backend first (3 TDD tasks), then Android (2 tasks, assembleDebug-gated). Streaming = `llm.stream()` generator → `chat_service.stream_message()` (persists both rows) → SSE `StreamingResponse`; Android reads it with raw OkHttp. Metrics computed on demand from Activities + DailySummary.

**Spec:** `docs/superpowers/specs/2026-07-08-chat-graphs-design.md`
**Branch:** `feat/chat-graphs` (worktree `C:/Users/dariu/Documents/GithubRepos/Splitrail/.worktrees/chat-v2`).
**Backend tests:** CWD `<worktree>/backend-fastapi`, interpreter `& "C:/Users/dariu/Documents/GithubRepos/Splitrail/.worktrees/rebrand-crux/backend-fastapi/.venv/Scripts/python.exe" -m pytest -q`. Baseline: **90 passed**.
**Android build:** CWD `<worktree>/android-native`, `.\gradlew.bat assembleDebug`.

---

### Task 1: DELETE /chat/history + PB purge (backend)

**Files:** Modify `app/routers/chat.py`, `app/chat_service.py:25`, `app/report_generator.py:26`, `app/schemas.py` (GateBlock), `app/routers/dashboard.py:57`, `tests/test_chat.py`, `tests/test_dashboard.py`.

- [ ] Failing tests — append to `tests/test_chat.py`:
```python
def test_clear_history(client):
    client.post("/chat", json={"message": "hello"})
    r = client.delete("/chat/history")
    assert r.status_code == 200 and r.json()["deleted"] == 2
    assert client.get("/chat/history").json() == []
    assert client.delete("/chat/history").json()["deleted"] == 0
```
And in `tests/test_dashboard.py` replace the `assert d["gate"]["pb"] == 6.91` line with `assert "pb" not in d["gate"]`.
- [ ] Run → FAIL (405 on DELETE; pb still present).
- [ ] Implement: in `app/routers/chat.py` add:
```python
@router.delete("/history")
def clear_history(db: Session = Depends(get_db)):
    deleted = db.query(ChatMessage).delete()
    db.commit()
    return {"deleted": deleted}
```
Purge: `chat_service.py` SYSTEM_PROMPT `"former national 60m champion (PB 6.91),"` → `"former national 60m champion,"`; same parenthetical removal in `report_generator.py`; delete `pb: float = 6.91` from `GateBlock` in `schemas.py`; drop `pb=6.91,` from the demo `GateBlock(...)` in `routers/dashboard.py`. Grep `6.91|6,91` over `backend-fastapi/app` → zero hits.
- [ ] Full suite → 91 passed. Commit: `feat: DELETE /chat/history; forget the 6.91 PB (prompts, schema, demo)`

---

### Task 2: Streaming chat (backend)

**Files:** Modify `app/llm.py`, `app/chat_service.py`, `app/routers/chat.py`; Test `tests/test_chat.py`, `tests/test_llm.py`.

- [ ] Failing tests — append to `tests/test_chat.py`:
```python
def test_chat_stream_offline_sse(client, db):
    with client.stream("POST", "/chat/stream", json={"message": "km this week?"}) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        lines = [ln for ln in r.iter_lines() if ln]
    assert lines[-1] == "data: [DONE]"
    import json as _json
    tokens = [_json.loads(ln[6:])["t"] for ln in lines[:-1] if ln.startswith("data: ")]
    assert "OFFLINE MODE" in "".join(tokens)
    history = client.get("/chat/history").json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert "OFFLINE MODE" in history[-1]["content"]
```
And to `tests/test_llm.py` (mock the provider stream — read that file's existing mocking style first):
```python
def test_stream_relays_openrouter_deltas(monkeypatch):
    from app import llm

    class _Delta:
        def __init__(self, c): self.content = c
    class _Choice:
        def __init__(self, c): self.delta = _Delta(c)
    class _Chunk:
        def __init__(self, c): self.choices = [_Choice(c)]
    class _Completions:
        def create(self, **kw):
            assert kw.get("stream") is True
            return iter([_Chunk("Hel"), _Chunk(None), _Chunk("lo")])
    class _Chat:
        completions = _Completions()
    class _Client:
        chat = _Chat()
    monkeypatch.setattr(llm, "_openai_client", lambda s: _Client())
    out = list(llm.stream(system="s", messages=[{"role": "user", "content": "x"}]))
    assert "".join(out) == "Hello"
```
- [ ] Run → FAIL (no `llm.stream`, 404 /chat/stream).
- [ ] Implement `app/llm.py`:
```python
def stream(system: str, messages: list[dict], max_tokens: int = 1000):
    """Yield text deltas from the configured provider."""
    s = get_settings()
    if s.llm_provider == "anthropic":
        yield from _anthropic_stream(s, system, messages, max_tokens)
    else:
        yield from _openrouter_stream(s, system, messages, max_tokens)


def _openrouter_stream(s, system, messages, max_tokens):
    client = _openai_client(s)
    resp = client.chat.completions.create(
        model=s.openrouter_model, max_tokens=max_tokens, stream=True,
        messages=[{"role": "system", "content": system}, *messages],
    )
    for chunk in resp:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def _anthropic_stream(s, system, messages, max_tokens):
    import anthropic

    client = anthropic.Anthropic(api_key=s.anthropic_api_key)
    with client.messages.stream(model=s.anthropic_model, max_tokens=max_tokens,
                                system=system, messages=messages) as stream:
        yield from stream.text_stream
```
`app/chat_service.py` — add (reusing the module's existing pieces; keep `send_message` unchanged):
```python
def stream_message(db: Session, message: str):
    """Yield reply tokens; persist both turns when the stream completes."""
    history = list(reversed(db.scalars(
        select(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(HISTORY_TURNS)
    ).all()))
    db.add(ChatMessage(role="user", content=message))
    db.commit()
    context = build_context(db)

    parts: list[str] = []
    if llm.is_configured():
        msgs = [{"role": "user" if m.role == "user" else "assistant", "content": m.content}
                for m in history] + [{"role": "user", "content": message}]
        try:
            for token in llm.stream(system=SYSTEM_PROMPT + json.dumps(context),
                                    messages=msgs, max_tokens=1000):
                parts.append(token)
                yield token
        except Exception as e:
            logger.error("Claude stream failed: %s", e)
            tail = " — SIGNAL LOST" if parts else f"SIGNAL LOST — Claude call failed ({e})."
            parts.append(tail)
            yield tail
    else:
        fallback = _fallback_reply(context)
        parts.append(fallback)
        yield fallback

    db.add(ChatMessage(role="assistant", content="".join(parts)))
    db.commit()
```
`app/routers/chat.py` — add:
```python
import json

from fastapi.responses import StreamingResponse


@router.post("/stream")
def chat_stream(payload: ChatIn, db: Session = Depends(get_db)):
    def _events():
        for token in chat_service.stream_message(db, payload.message):
            yield f"data: {json.dumps({'t': token})}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(_events(), media_type="text/event-stream")
```
NOTE: the `db` session from `get_db` stays open for the generator's lifetime (FastAPI closes it after the response finishes) — verify the offline test passes with both rows persisted; if the session closes early, create a dedicated `SessionLocal()` inside `_events()` instead and close it in a `finally`.
- [ ] Full suite → 93 passed. Commit: `feat: streaming chat — llm.stream + SSE POST /chat/stream`

---

### Task 3: Report metrics (backend)

**Files:** Create nothing new except tests; Modify `app/routers/reports.py`, `app/schemas.py`. Test: append to `tests/test_reports.py` (read it first for fixture style — it creates reports via `POST /reports/generate` in offline mode).

- [ ] Failing test — append to `tests/test_reports.py`:
```python
def test_report_metrics_shape_and_days(client, db):
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    client.post("/activities", json={
        "type": "easy_run", "start_time": now.isoformat(),
        "duration_s": 2400, "distance_m": 8000})
    client.post("/reports/generate")
    rep = client.get("/reports").json()[0]

    r = client.get(f"/reports/{rep['id']}/metrics")
    assert r.status_code == 200
    days = r.json()["days"]
    assert len(days) == 7
    assert set(days[0]) >= {"day", "km", "vert_m", "mood_valence", "sessions"}
    assert any(abs(d["km"] - 8.0) < 1e-6 for d in days)
    assert client.get("/reports/9999/metrics").status_code == 404
```
NOTE: verify how `POST /reports/generate` picks its period (read `report_generator.py`) — if the current in-progress week is used the activity above lands inside it; if it's the PREVIOUS full week, date the activity inside that period instead. Adjust the activity's `start_time` accordingly so the km assertion holds deterministically.
- [ ] Run → FAIL (404 metrics route).
- [ ] Implement — `app/schemas.py`:
```python
class MetricDay(BaseModel):
    day: date
    km: float = 0
    vert_m: float = 0
    mood_valence: float | None = None
    sessions: int = 0


class ReportMetricsOut(BaseModel):
    days: list[MetricDay]
```
`app/routers/reports.py` (match its existing imports/style; it already has get_db etc.):
```python
@router.get("/{report_id}/metrics", response_model=ReportMetricsOut)
def report_metrics(report_id: int, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    start_dt = datetime.combine(report.period_start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(report.period_end + timedelta(days=1), time.min, tzinfo=timezone.utc)
    activities = db.scalars(select(Activity).where(
        Activity.start_time >= start_dt, Activity.start_time < end_dt)).all()
    summaries = {s.day: s for s in db.scalars(select(DailySummary).where(
        DailySummary.day >= report.period_start, DailySummary.day <= report.period_end)).all()}

    days = []
    d = report.period_start
    while d <= report.period_end:
        day_acts = [a for a in activities if a.start_time.date() == d]
        days.append(MetricDay(
            day=d,
            km=round(sum((a.distance_m or 0) / 1000 for a in day_acts
                         if a.mode == EffortMode.aerobic), 2),
            vert_m=round(sum(a.elevation_gain_m or 0 for a in day_acts
                             if a.mode == EffortMode.loaded), 1),
            mood_valence=summaries[d].mood_valence if d in summaries else None,
            sessions=len(day_acts),
        ))
        d += timedelta(days=1)
    return ReportMetricsOut(days=days)
```
(Adjust imports: `datetime, time, timedelta, timezone`, `HTTPException`, `Activity`, `DailySummary`, `EffortMode`, new schemas.)
- [ ] Full suite → 94 passed. Commit: `feat: GET /reports/{id}/metrics (per-day km/vert/mood/sessions)`

---

### Task 4: Android — CLEAR + streaming chat

**Files (under `android-native/app/src/main/java/com/darius/crux/`):** Modify `network/CruxApi.kt` (DELETE endpoint), `network/RetrofitClient.kt` (expose the OkHttpClient or a base-url helper if needed), `data/repository/ChatRepository.kt`, `ui/viewmodel/ChatViewModel.kt`, `ui/screens/ChatScreen.kt`.
READ FIRST: all five files above + `network/ApiConfig.kt`.

- [ ] `CruxApi`: `@DELETE("chat/history") suspend fun clearChatHistory(): Response<Unit>` (match conventions; a Map return also fine).
- [ ] Streaming in `ChatRepository`: a `fun streamMessage(message: String): Flow<String>` using OkHttp directly:
  - Build a dedicated client from the shared one with `readTimeout(120, SECONDS)`.
  - POST `ApiConfig.BASE_URL + "chat/stream"` body `{"message": ...}` (`application/json`).
  - Read `response.body!!.source()` line-by-line (`readUtf8Line()`): lines starting `data: ` → payload; `[DONE]` → close; else JSON-parse `{"t": token}` and `emit(token)`. Wrap in `flow { }.flowOn(Dispatchers.IO)`.
- [ ] `ChatViewModel`: on send — optimistic user row (existing behavior), append an empty assistant row, collect the flow appending each token to that row's content (update StateFlow immutably). On flow exception BEFORE any token: fall back to the existing non-streaming send path and replace the assistant row with its reply. After tokens: append " — SIGNAL LOST". Add `clearHistory()` calling the DELETE endpoint then emptying local state.
- [ ] `ChatScreen`: header gains `CLEAR` (labelSmall, Graphite) — tap 1 → text becomes `SURE?` (GateRed) with a 3s `LaunchedEffect` timeout back to CLEAR; tap 2 within window → `viewModel.clearHistory()`. Keep MEET SHEET (no dialogs/cards).
- [ ] Build → BUILD SUCCESSFUL. Commit: `feat(android): streaming chat replies + clear history`

---

### Task 5: Android — report charts + PB purge

**Files:** Modify `network/DTOs.kt`, `network/CruxApi.kt`, `data/repository/ReportsRepository.kt`, `ui/viewmodel/ReportDetailViewModel.kt`, `ui/screens/ReportDetailScreen.kt`, `data/SampleData.kt`, `data/model/DashboardModels.kt`; Create `ui/components/ReportCharts.kt`.
READ FIRST: `ui/components/MoodTrace.kt` (Canvas style), `ui/screens/ReportDetailScreen.kt`, `ui/theme/Color.kt` (Steel/Scree/Ink), plus the DTO/API/repo files.

- [ ] DTOs (house conventions): `MetricDayDTO(day, km, vert_m, mood_valence, sessions)`, `ReportMetricsDTO(days)`. API: `@GET("reports/{id}/metrics") suspend fun getReportMetrics(@Path("id") id: Int): Response<ReportMetricsDTO>`.
- [ ] `ReportDetailViewModel`: fetch metrics alongside the report (independent try/catch → null hides the section).
- [ ] `ui/components/ReportCharts.kt`: `WeekInNumbers(days: List<MetricDayDTO>)` — engraved label `WEEK IN NUMBERS`, then three ~48dp-tall Canvas charts stacked with 8dp gaps, each with a labelSmall caption + right-aligned mono max value:
  - `KM` — bars per day, Steel; zero-days empty.
  - `VERT` — bars per day, Scree.
  - `MOOD` — polyline of non-null valences, Ink, dots at points; gaps break the line (mirror MoodTrace's approach).
  Draw with plain `Canvas`, hairline baseline (Ink 22% alpha) like the other instruments.
- [ ] `ReportDetailScreen`: render `WeekInNumbers` between the header and markdown body when metrics is non-null.
- [ ] PB purge: remove `pb` from `GateBlockDTO` (DTOs.kt) and `GateBlock` (data/model/DashboardModels.kt) and the `pb = 6.91,` line in `SampleData.kt`. Grep `6.91` over `android-native/app/src` → zero hits.
- [ ] Build → BUILD SUCCESSFUL. Commit: `feat(android): WEEK IN NUMBERS charts on reports; PB fully forgotten`

---

### Task 6: Verify + rollout
- [ ] Backend suite → 94 passed; `assembleDebug` → BUILD SUCCESSFUL.
- [ ] (Post-merge, manual) droplet pull + compose up; verify SSE streams through Caddy live (`curl -N -X POST https://api.crux.com.im/chat/stream ...` shows incremental tokens; if buffered, add `flush_interval -1` to the Caddyfile reverse_proxy and redeploy); rebuild APK; adb install; on-phone: stream a chat, CLEAR, open a report with charts, ask chat about sprint PB (must not say 6.91).

## Verification summary
T1→91, T2→93, T3→94 backend tests; T4/T5 assembleDebug; T6 live SSE + phone checks.
