# Splitrail — Feature Backlog

Additions folded into the existing build order (see root `README.md` → Build order).
Each feature below is its own future spec → plan → implementation cycle; this doc is
the capture list and dependency map, not a spec.

## Features

### 1. Voice logging
Extends the speech-parsing experience from ListManagerApp.
- Voice-note capture flow: record right after a session, bilingual RO/EN.
- **Two-stage extraction pipeline:** deterministic parser first (fast, cheap, common
  phrasing) → LLM fallback for ambiguous/complex descriptions. Same pipeline routes
  "legs felt heavy" differently from "saw ice on the trail".
- Store **both** the raw transcript **and** extracted structured fields (session type,
  perceived effort, subjective notes) alongside the day's Strava-synced objective data.
- Data model: new `VoiceLog` table — timestamp, transcript, extracted structured
  fields, linked `Activity` id.

### 2. Subjective–objective correlation analysis
New job for the Claude analysis layer.
- Extend the weekly Celery report job to cross-reference voice-note sentiment/content
  against objective metrics (pace, HR, sleep, elevation gain).
- Example flag: "you report heavy legs disproportionately on sprint days following
  >800 m elevation-gain hikes."
- Depends on: `VoiceLog` table (feature 1).

### 3. Interference-effect coaching
New domain logic grounded in sports science.
- Rule/heuristic layer (start simple, not ML) checking session sequencing against known
  concurrent-training interference patterns — e.g. flag a long aerobic session within
  48 h of a max-velocity/sprint session.
- Feed flags as **structured input** into the Claude weekly report so the LLM explains
  *why* a flag was raised (cite the pattern), not just a bare warning.
- Candidate for a small reference **knowledge file** (markdown doc of concurrent-training
  literature) included in the report-generation prompt as context — like a skill file.

### 4. Mood / audio-priming analysis
Extends the planned Spotify integration.
- Once Spotify sync is in: correlate pre-session listening (valence/energy/tempo in the
  hour before a logged activity) against session performance → personalized "what you
  actually listen to before your best sessions" insight.
- Stretch: auto-suggest a pre-session playlist from your own historical best-session
  audio profile. (Not MVP.)
- Depends on: Spotify sync (build step 4).

### 5. Mountaineering pacing model
Later-phase; data-hungry, sequence last.
- Given a planned ascent profile (distance, elevation gain), estimate a personalized
  effort/pacing target from your own historical sustained-effort data (not generic zones).
- Depends on: several months of HR/pace history from voice logging + Strava sync.

## Mapping onto the existing build order

| Existing step | Addition |
|---|---|
| Step 3 (real Strava data on dashboard) | Add `VoiceLog` data model now, even before capture UI |
| Step 4 (Spotify + mood chart) | Pre-session listening correlation once Spotify sync works |
| Step 5 (Claude weekly reports) | Interference-effect flags + subjective/objective correlation as new report-prompt inputs |
| Step 6 (chat) | Voice-note capture UI — new Android screen + backend endpoint (or its own Step 6.5) |
| New Step 8 | Mountaineering pacing model, once enough history exists |

## Dependency order (what unlocks what)

```
VoiceLog table (foundation)
  ├─ voice capture UI (Android) + capture endpoint (backend)
  ├─ subjective/objective correlation  →─┐
interference-effect rules + knowledge file →─┤→ richer Claude weekly report
Spotify sync → audio-priming correlation ───┘
(months of history) → mountaineering pacing model
```

Note: the in-flight **hosting + OpenRouter provider** work
(`plans/2026-07-05-hosting-and-openrouter.md`) is orthogonal — it changes *how* the
report/chat LLM calls are made, and all of features 2–5 that hit the LLM will ride on
that same `app/llm.py` abstraction.
