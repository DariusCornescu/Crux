# OVERNIGHT-LOG — autonomous run (handoff: 2026-07-05-overnight-fable-handoff.md)

Decision/blocker log, in execution order. Baseline at start: 18 tests passing.

## Setup / state verification
- **DISCREPANCY vs handoff "Current state":** the handoff says Phase 0 Task 1
  (config provider fields) is already applied. It is NOT — `app/config.py` had no
  `llm_provider`/`openrouter_*` fields and `anthropic_model` was still
  `claude-sonnet-5`. Resolution: executed Task 1 as written in the hosting plan
  (lowest risk — the plan is explicit about the exact fields).
- **No `docker` binary in this environment.** The Phase 0 gate
  (`docker compose ... config --quiet`) cannot be run literally. Resolution:
  structurally validated both compose files with a YAML parser that tolerates the
  `!reset` tag, and left the real `docker compose config` command in
  MORNING-CHECKLIST for the human. Kept `ports: !reset []` (requires Compose
  v2.24+; get.docker.com installs current, and the plan documents the loopback
  fallback).
- `.env` exists (user-created). Per Contract rule 4 its values were never read
  into logs/output; the provider block was appended programmatically, preserving
  existing content, keys left empty.

## Phase 0 — OpenRouter + deploy files
- Tasks 1–8 executed per the hosting plan. Suite: 23 passing after Task 5.
- **Test-hygiene addition** to the plan's `tests/test_llm.py`: an autouse fixture
  that runs `get_settings.cache_clear()` after each test. Without it, the lru_cache
  keeps monkeypatched Settings (e.g. a fake anthropic key) alive after monkeypatch
  restores env, which would poison later offline tests into attempting real calls.
- **Found + fixed pre-existing corruption:** `docker-compose.yml` was truncated
  mid-file (lost the tail of `beat` and the `volumes:` block) — an artifact of the
  intermittent mounted-folder write glitch noted in the previous session. Rewrote
  the full file; structural YAML validation passes. Because of this, the final
  verification step includes a whole-repo integrity sweep (py_compile everything,
  YAML/XML parses, Kotlin brace balance).
- `docker compose config` gate: **deferred to morning** (no docker binary here);
  structural validation done instead.
- Android Task 8 applied as code-only per handoff: BASE_URL = placeholder domain
  with TODO(domain); cleartext flag removed. NOT built/installed (human-gated).
  Note: until the domain exists, the app cannot reach a local backend over http —
  reverting BASE_URL to "http://10.0.2.2:8000/" (and temporarily re-adding the
  cleartext flag) is the documented local-dev fallback in ApiConfig.kt comments.

## Phase 1 — VoiceLog + two-stage extraction
- Migration `286c43fab6ec_voice_logs` generated; FK follows the naming convention
  (`fk_voice_logs_activity_id_activities`); drift guard green.
- Small behavior choices (not settled by the handoff, all low-risk):
  - Keyword matching runs on lowercase, diacritic-stripped text (NFD strip) so
    "gheață"/"gheata", "tură"/"tura" both match the ASCII tables.
  - Keyword table is ordered with `ruck`/`rucsac` before `hike` so "tură cu
    rucsac" classifies as ruck.
  - Deterministic path leaves `notes=None` (it cannot summarize); only the LLM
    path fills `notes`.
  - If the LLM extraction reply has no parseable ```json block, extraction falls
    back to the deterministic best effort (method="deterministic") rather than
    failing the request.

## Phase 2 — subjective↔objective correlation
- `subjective` block and `subjective_flags` are both computed inside
  `build_week_summary` (it already holds db + activities). Flags implemented:
  `heavy_legs_after_big_vert` (same day or +1 day, vert > 800 m).
- Offline fallback report gained a "## Subjective" section with log/flag counts.

## Phase 3 — interference + knowledge file
- Rules implemented per handoff. "Long aerobic" for `sprint_before_recovery`
  reuses the same 12 km threshold as `aerobic_blunts_sprint` (the handoff said
  "long" without a number for that rule; one shared constant is the simplest
  consistent reading).
- `pattern_ref` anchors (`aerobic-before-speed`, `recovery-windows`,
  `structural-fatigue`) appear verbatim in the knowledge-file headings; a test
  keeps rules and knowledge file in sync.
- Knowledge text is appended to the system prompt in `_claude_report` only
  (kept out of chat per handoff, to save tokens).

## Phase 4 — audio priming
- `n_best`/`n_rest` count sessions that actually contributed a priming profile
  (sessions with no tracks in the 60-min window are excluded from both groups) —
  the handoff didn't pin this down; counting non-contributing sessions would
  make the averages misleading.
- Top quartile = `max(1, n // 4)` per mode among metric-bearing sessions.
- **Deferred (per handoff): playlist auto-suggest stretch — not built.**

## Phase 5 — pacing model
- Implemented (did not stop after Phase 4). Additive Munter-style model as
  specified; `basis` reflects only the vertical-speed source (the primary
  driver) — flat speed may still fall back to 1.2 m/s independently; the
  response `notes` states both components explicitly.
- Tests are synthetic; the module docstring and endpoint notes both say
  real-data calibration is required.

## Final state
- Full suite: **55 passed** (baseline was 18). Drift guard green.
- Whole-repo integrity sweep after the earlier corruption finds: all Python
  compiles/parses, YAML/XML/TOML parse, Kotlin braces balanced.
- No secrets touched: `.env` keys appended empty; values never read or printed.
- Android: NOT built (no SDK here + human-gated). Code edits from Phase 0 Task 8
  only.
