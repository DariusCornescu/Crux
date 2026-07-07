# Splitrail — Overnight Autonomous Build Handoff (for Fable)

> **You are an autonomous agent (Fable 5) running this UNATTENDED overnight. No human
> will answer questions until morning.** This document is your complete brief. Read the
> **Autonomy Contract** first and obey it for every phase. When a decision is already
> made here, implement it — do not re-litigate. When you hit something genuinely
> ambiguous or architecturally significant that this doc does NOT settle, do NOT guess:
> write an entry in the decision log and either pick the clearly-lowest-risk option
> (documenting why) or skip that unit and continue with the next.

Working dir: `PersonalApp/backend-fastapi/` (backend) and `PersonalApp/android-native/`
(app). Run backend tests from `backend-fastapi/` with `python -m pytest -q`.

Related docs:
- Spec: `docs/superpowers/specs/2026-07-05-hosting-and-openrouter-design.md`
- Detailed Phase 0 plan: `docs/superpowers/plans/2026-07-05-hosting-and-openrouter.md`
- Backlog + dependency map: `docs/BACKLOG.md`

---

## Autonomy Contract (READ FIRST — applies to every phase)

1. **TDD, always.** For each unit: write the failing test → run it, see it fail →
   implement the minimum → run it, see it pass. No implementation without a test first.
2. **Definition of Done for the whole run:** all code written, `python -m pytest -q`
   is **green**, the migration drift-guard test (`tests/test_migrations.py`) passes,
   and the decision log is up to date. Deploy is NOT part of DoD (see Human-Gated).
3. **Verification is the test suite, not the network.** There is **no API key** and
   **no deployed server** available to you. Never make real OpenRouter/Anthropic/Strava/
   Spotify calls. All LLM tests mock the provider clients (see `tests/test_llm.py` as
   the pattern). All external-HTTP tests use the `FakeResponse` pattern in
   `tests/conftest.py`.
4. **No secrets, ever.** Do not invent, hardcode, or commit API keys. Leave key fields
   empty in `.env`. Do not read the user's real `.env` values into code or logs.
5. **No git.** This project is not version-controlled. There are no commits. After each
   phase, run the full suite as the checkpoint.
6. **Every `app/models.py` change REQUIRES an Alembic migration.** After editing models,
   run: `alembic revision --autogenerate -m "<desc>"` from `backend-fastapi/`, inspect
   the generated file in `alembic/versions/` for correctness (right table/columns, FK
   uses the naming convention), then run `python -m pytest tests/test_migrations.py -q`
   until the drift guard passes. Migrations must respect the naming convention in
   `app/database.py` (Alembic autogenerate honors it automatically).
7. **Stop-and-log, don't guess.** For any architecturally significant choice this doc
   does not settle (new external dependency, a schema tradeoff, a public API-contract
   ambiguity): append to `docs/superpowers/OVERNIGHT-LOG.md` with the question, the
   options, and what you chose + why. Prefer the lowest-risk reversible option. If you
   cannot proceed safely, skip that unit, log it, and move to the next.
8. **Preserve existing behavior.** The deterministic offline fallbacks
   (`report_generator._fallback_report`, `chat_service._fallback_reply`) must keep
   working when no provider key is set. Existing tests must stay green.
9. **Phase order is dependency order.** Do phases in the numbered order. If a phase's
   prerequisite failed, skip dependent phases and log it. A partial-but-green result is
   better than a broken everything.
10. **Keep files focused.** New domain logic goes in new flat modules (`app/voice_extract.py`,
    `app/interference.py`, etc.), matching the existing flat-module style. Don't refactor
    unrelated code.

### Decision log
Create `docs/superpowers/OVERNIGHT-LOG.md` at the start. Append: timestamp-free entries
(you cannot call the clock), phase, decision/blocker, resolution. This is the first thing
the human reads in the morning.

### Human-Gated items — DO NOT attempt; list them in the morning checklist
- Creating the DigitalOcean Droplet, buying/pointing a domain, DNS.
- Providing `OPENROUTER_API_KEY` (and choosing/paying for a model).
- Running `scp` / `docker compose up` on the server; issuing TLS certs.
- Installing the APK on the physical phone; granting notification permission.
- Updating Strava/Spotify OAuth redirect URIs in their dashboards.
- Any real end-to-end LLM/network validation.

At the end, write `docs/superpowers/MORNING-CHECKLIST.md` enumerating exactly these
human steps in order, with the concrete commands (pull them from `docs/DEPLOY.md`).

---

## Current state (already applied — verify, don't redo)
- `app/config.py` **already has** `llm_provider`, `openrouter_api_key`, `openrouter_model`,
  and `anthropic_model` fixed to `claude-sonnet-4-6`. Phase 0 Task 1 is DONE. Verify with
  `python -c "from app.config import get_settings; print(get_settings().llm_provider)"`
  → `openrouter`. If already correct, skip Phase 0 Task 1.
- Everything else in Phase 0 (Tasks 2–8) is NOT done yet.
- `ListeningSession` (Spotify), `Activity`, `DailySummary`, `Report`, `ChatMessage`
  models already exist. Strava + Spotify sync are implemented (build steps 2 & 4).

---

## Phase 0 — Hosting + OpenRouter provider switch
**Execute `docs/superpowers/plans/2026-07-05-hosting-and-openrouter.md` Tasks 2–8**
(Task 1 already done). That plan is bite-sized and complete; follow it verbatim. It
introduces `app/llm.py` (`complete()`, `is_configured()`), refactors `report_generator`
and `chat_service` to use it, adds `openai` to requirements, updates env files, and
creates the deploy files (`Caddyfile`, `docker-compose.prod.yml`, `docs/DEPLOY.md`).

**Phase 0 gate:** `python -m pytest -q` green; `docker compose -f docker-compose.yml -f
docker-compose.prod.yml config --quiet` prints VALID. Android edits (Task 8) — make the
code edits but note the real domain is unknown, so leave `BASE_URL` as
`https://your-domain.example/` with a `TODO(domain)` comment; do NOT build/install the APK.

Everything downstream (Phases 2–5 LLM calls) uses `app/llm.py`, so Phase 0 must land first.

---

## Phase 1 — VoiceLog data model + capture + two-stage extraction
Backlog feature 1. Foundation for Phases 2–3.

### Design decisions (pre-made — implement as written)

**Model** (`app/models.py`, new class; then migration per Contract rule 6):
```python
class VoiceLog(Base):
    __tablename__ = "voice_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id"), nullable=True)
    lang: Mapped[str | None] = mapped_column(String(8), nullable=True)      # "ro" | "en" | "mixed"
    transcript: Mapped[str] = mapped_column(Text)
    # --- extracted structured fields ---
    perceived_effort: Mapped[int | None] = mapped_column(Integer, nullable=True)   # RPE 1-10
    session_type: Mapped[ActivityType | None] = mapped_column(Enum(ActivityType), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)         # subjective summary
    extraction_method: Mapped[str] = mapped_column(String(16), default="none")  # deterministic|llm|none
    extracted: Mapped[dict | None] = mapped_column(JSON, nullable=True)    # full struct: {symptoms:[], terrain:[], raw_fields...}
```
Import `ForeignKey` from sqlalchemy. The FK name auto-follows the naming convention.

**Activity linkage:** if the request supplies `activity_id`, use it. Otherwise link to the
**most recent Activity on the same calendar day (UTC) as `created_at`**, if one exists;
else leave null. Put this resolution in the endpoint, not the model.

**Extraction module** `app/voice_extract.py`:
```python
def extract(transcript: str, lang: str | None = None) -> dict:
    """Two-stage. Returns:
    {"perceived_effort": int|None, "session_type": str|None (ActivityType value),
     "notes": str|None, "symptoms": [str], "terrain": [str], "method": "deterministic"|"llm"}
    """
```
- **Stage 1 — deterministic** (`_deterministic(transcript, lang) -> dict | None`):
  bilingual keyword/regex tables. Return a dict when it confidently finds structure,
  else `None` to trigger the LLM. Minimum tables (extend as sensible, log additions):
  - RPE: regex `\b(?:rpe|efort|effort)\s*(\d{1,2})\b` and bare `\b([1-9]|10)\s*/\s*10\b`.
  - session_type keywords → ActivityType: RO/EN {"sprint"/"sprinturi"→sprint,
    "tempo"→tempo, "alergare ușoară"/"easy run"→easy_run, "tură"/"hike"/"drumeție"→hike,
    "ruck"/"rucsac"→ruck, "forță"/"strength"→strength}.
  - symptoms: {"heavy legs"/"picioare grele"→"heavy_legs", "tired"/"obosit"→"fatigue",
    "great"/"puternic"/"strong"→"strong", "sore"/"dureri"→"soreness"}.
  - terrain: {"ice"/"gheață"→"ice", "snow"/"zăpadă"→"snow", "mud"/"noroi"→"mud",
    "wind"/"vânt"→"wind"}.
  - "Confident" = found at least an RPE OR a session_type OR ≥1 symptom AND transcript
    is short/simple (≤ 25 words). Longer/ambiguous → return None → LLM.
- **Stage 2 — LLM fallback** (`_llm(transcript, lang) -> dict`): call
  `llm.complete(system=VOICE_EXTRACT_PROMPT, messages=[{"role":"user","content":transcript}],
  max_tokens=400)`, where the prompt instructs a strict JSON object with the same keys and
  ends with a fenced ```json block; parse it with the same regex approach
  `report_generator` uses. If `llm.is_configured()` is False, DO NOT call the LLM — return
  the best-effort deterministic dict (even if low confidence) with `method="deterministic"`.
  This keeps the feature testable offline.

**Schemas** (`app/schemas.py`):
```python
class VoiceLogCreate(BaseModel):
    transcript: str
    lang: str | None = None
    activity_id: int | None = None
    created_at: datetime | None = None

class VoiceLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    activity_id: int | None = None
    lang: str | None = None
    transcript: str
    perceived_effort: int | None = None
    session_type: ActivityType | None = None
    notes: str | None = None
    extraction_method: str
    extracted: dict | None = None
```

**Router** `app/routers/voice_logs.py` (mirror `activities.py`; register in `app/main.py`
with the other `app.include_router(...)` lines):
- `POST /voice-logs` → run `voice_extract.extract`, resolve `activity_id`, persist, return `VoiceLogOut` (201).
- `GET /voice-logs?limit=50` → newest-first list.

### Tests (`tests/test_voice_logs.py`, `tests/test_voice_extract.py`)
- Deterministic: `extract("RPE 8, picioare grele după sprinturi")` → perceived_effort=8,
  symptoms contains "heavy_legs", session_type="sprint", method="deterministic".
- Offline LLM path: with no key (test env), a long ambiguous transcript still returns a
  dict with `method="deterministic"` (no network).
- LLM path with monkeypatched `voice_extract._llm` returning a fixed dict → assert it's
  used for a long transcript.
- Endpoint: POST a transcript → 201, fields populated; same-day Activity gets linked;
  GET returns it.

**Phase 1 gate:** migration generated + drift guard passes; full suite green.

---

## Phase 2 — Subjective ↔ objective correlation (report input)
Backlog feature 2. Depends on Phase 1.

### Design decisions
- New helper in `report_generator.py`: extend `build_week_summary` to attach a
  `"subjective"` key: for the week's days, gather `VoiceLog` rows and emit
  `[{"day","perceived_effort","notes","symptoms","linked_mode": <EffortMode value or None>}]`
  (linked_mode from the linked Activity's `.mode`, if any).
- New pure module `app/correlations.py`:
  ```python
  def subjective_flags(activities: list[Activity], voice_logs: list[VoiceLog]) -> list[dict]:
      """Deterministic cross-references. Each flag: {code, message, evidence:{...}}."""
  ```
  Implement at least: **"heavy_legs_after_big_vert"** — a VoiceLog with `"heavy_legs"`
  reported on/one day after a `loaded` activity with `elevation_gain_m > 800`. Message
  cites the numbers.
- Feed both into the report: add the `subjective` block + `subjective_flags` to the
  summary dict passed to `_claude_report`, and extend `SYSTEM_PROMPT` with a sentence:
  "When subjective reports are present, cross-reference them against the objective
  numbers and explain correlations concretely (cite the day and the metric)."
- The deterministic `_fallback_report` should mention the count of subjective flags so the
  offline path stays informative.

### Tests (`tests/test_correlations.py`, extend `tests/test_reports.py`)
- `subjective_flags` fires on a fixture: loaded activity vert=900 + next-day voice log
  "heavy legs" → one flag with the right code; no flag when vert=400.
- `build_week_summary` includes the `subjective` block when voice logs exist.

**Phase 2 gate:** full suite green.

---

## Phase 3 — Interference-effect coaching + knowledge file
Backlog feature 3. Depends on nothing beyond existing Activity data (can run after Phase 0).

### Design decisions
- New pure module `app/interference.py`:
  ```python
  def detect(activities: list[Activity]) -> list[dict]:
      """Session-sequencing interference flags. Each: {code, message, activity_ids:[int], pattern_ref}."""
  ```
  Rules (windows use `start_time`):
  - **`aerobic_blunts_sprint`**: a `explosive` session within **48h after** an `aerobic`
    session with `distance_m >= 12000` (long aerobic) → neural quality likely blunted.
  - **`sprint_before_recovery`**: an `aerobic` long session within **48h after** an
    `explosive` session → compromised sprint adaptation / insufficient recovery.
  - **`loaded_before_sprint`**: an `explosive` session within **48h after** a `loaded`
    session with `elevation_gain_m > 800` → structural fatigue into neural work.
  `pattern_ref` is a short anchor string (e.g. `"concurrent-training#interference"`) that
  matches a heading in the knowledge file.
- **Knowledge file** `app/knowledge/concurrent_training.md`: a concise, sourced-in-spirit
  markdown summary of concurrent-training interference (the "interference effect",
  aerobic-before-strength/speed, ~recovery windows, molecular-signaling one-liner). Keep
  it factual and short (~1 page); use plain phrasing, no fabricated citations — frame as
  "established training-science consensus." Headings match the `pattern_ref` anchors.
- Report integration: pass `interference.detect(activities)` into the summary as
  `"interference_flags"`, and include the knowledge file's text in the report call as a
  **second system/context block** so the LLM explains *why* each flag matters citing the
  pattern. Simplest: append `"\n\nREFERENCE (concurrent training):\n" + knowledge_text` to
  the system prompt in `_claude_report` only (keep it out of chat to save tokens).
- Extend `SYSTEM_PROMPT` / report instruction: "For each interference flag provided,
  explain the mechanism using the REFERENCE, not just a warning."

### Tests (`tests/test_interference.py`)
- Each rule fires on a targeted 2-activity fixture and does NOT fire when the gap is >48h
  or the threshold isn't met. Assert `activity_ids` and `code`.
- A test asserting `app/knowledge/concurrent_training.md` exists and is non-empty and that
  every `pattern_ref` produced by `detect` on a broad fixture appears as a heading anchor
  substring in the file (keeps rules and knowledge in sync).

**Phase 3 gate:** full suite green.

---

## Phase 4 — Mood / audio-priming analysis
Backlog feature 4. Depends on `ListeningSession` (already present) + Activity.

### Design decisions
- New pure module `app/audio_priming.py`:
  ```python
  PRIMING_WINDOW_MIN = 60

  def priming_profile(activity: Activity, listening: list[ListeningSession]) -> dict | None:
      """Avg valence/energy/tempo of tracks played within PRIMING_WINDOW_MIN before start_time.
      Returns {"n": int, "valence": float|None, "energy": float|None, "tempo": float|None} or None if no tracks."""

  def best_session_audio(activities: list[Activity], listening: list[ListeningSession]) -> dict:
      """Compare priming profiles of top-quartile sessions vs the rest.
      'Best' per mode: explosive→lowest best split; aerobic→lowest avg_pace_s_per_km;
      loaded→highest elevation_gain_m. Returns {"best": profile-avg, "rest": profile-avg, "n_best": int, "n_rest": int}."""
  ```
- Expose read-only endpoint `GET /insights/audio-priming` (new router
  `app/routers/insights.py`, registered in `main.py`) returning `best_session_audio` over
  the last 90 days. Also include a compact version in the chat context builder
  (`chat_service.build_context`) under key `"audio_priming"` so the chat can answer
  "what do I listen to before good sessions?".
- **Stretch (playlist auto-suggest): DO NOT build.** Log it in OVERNIGHT-LOG as deferred.

### Tests (`tests/test_audio_priming.py`)
- `priming_profile` averages only tracks inside the 60-min pre-window; returns None with
  no tracks; ignores tracks after start.
- `best_session_audio` splits sessions correctly on a fixture where the fastest sprint
  session was preceded by high-energy tracks.

**Phase 4 gate:** full suite green.

---

## Phase 5 — Mountaineering pacing model (lowest priority)
Backlog feature 5. Data-hungry; implement the heuristic + tests on synthetic fixtures,
clearly labeled as needing real-data calibration. If time/complexity runs long, it is
acceptable to STOP after Phase 4 — log Phase 5 as not-started. Do NOT half-build it.

### Design decisions (if attempted)
- New pure module `app/pacing.py`:
  ```python
  def sustained_vertical_speed(loaded_activities: list[Activity]) -> float | None:
      """Median m of elevation gain per hour across loaded sessions with vert+duration. None if no data."""

  def estimate(distance_m: float, elevation_gain_m: float, history: list[Activity]) -> dict:
      """Personalized effort/pacing target for a planned ascent.
      Uses sustained_vertical_speed (fallback to a documented default 400 m/h if no history)
      and aerobic avg pace for the flat-distance component. Returns
      {"est_duration_s": int, "basis": "personal"|"default", "vert_speed_m_per_h": float, "notes": str}."""
  ```
  Duration model (documented, simple, calibratable): `time = elevation_gain_m /
  vert_speed_m_per_h * 3600 + distance_m / assumed_flat_speed_m_s`, where
  `assumed_flat_speed_m_s` derives from aerobic history avg pace (fallback 1.2 m/s).
- Endpoint `POST /pacing/estimate` (add to `insights.py`) with body
  `{distance_m, elevation_gain_m}` → the estimate. Mark clearly in the response `basis`
  whether it used personal data or defaults.

### Tests (`tests/test_pacing.py`)
- `sustained_vertical_speed` computes the median on a fixture; None on empty.
- `estimate` uses personal speed when history exists (`basis="personal"`) and the default
  when it doesn't (`basis="default"`); duration scales with vert and distance.

**Phase 5 gate:** full suite green.

---

## Final steps (before you finish)
1. `python -m pytest -q` — must be fully green. If any test is red and you cannot fix it,
   leave it red ONLY if isolated, and log it prominently in OVERNIGHT-LOG.
2. Confirm `python -m pytest tests/test_migrations.py -q` passes (models ↔ migrations agree).
3. Write `docs/superpowers/MORNING-CHECKLIST.md`: the ordered human-gated steps (deploy via
   `docs/DEPLOY.md`, provide `OPENROUTER_API_KEY`, set domain in `Caddyfile` + Android
   `BASE_URL`, update OAuth redirect URIs, build+install APK), plus a short summary of what
   was built per phase and anything skipped/deferred.
4. Make sure `docs/superpowers/OVERNIGHT-LOG.md` reflects every decision and blocker.

## What "success in the morning" looks like
- All 5 phases implemented (Phase 5 optional), tests green, migrations consistent.
- No secrets committed; `.env` keys still empty.
- Two fresh docs: OVERNIGHT-LOG.md (decisions) and MORNING-CHECKLIST.md (your to-dos).
- Nothing deployed — that's the human's morning job, guided by DEPLOY.md.
