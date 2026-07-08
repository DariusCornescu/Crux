# Listening-Mood via ReccoBeats — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore listening-derived mood (valence/energy) by sourcing audio features from ReccoBeats instead of Spotify's dead endpoint, store the Spotify track id, feed recent tracks into the chat context, and backfill already-synced rows.

**Architecture:** Swap the one HTTP call in `app/spotify.py::_fetch_audio_features` to ReccoBeats (`GET /v1/audio-features?ids=…`, no auth, batched); everything downstream (`aggregate_daily_mood` → `DailySummary` → dashboard/audio-priming) is unchanged. Add a `spotify_track_id` column so tracks can be re-fetched (backfill). Add `recent_listening` to the chat snapshot.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, httpx, pytest (monkeypatch + `FakeResponse` helper in `tests/conftest.py`).

**Spec:** `docs/superpowers/specs/2026-07-08-mood-reccobeats-design.md`

**Branch:** `feat/mood-reccobeats` (worktree already created; spec committed).

**Key external fact:** ReccoBeats' `GET https://api.reccobeats.com/v1/audio-features?ids=<comma-separated Spotify ids>` returns `{"content": [ {"href": "https://open.spotify.com/track/<id>", "valence": .., "energy": .., "tempo": ..}, … ]}`. No API key. Map back to the Spotify id by stripping the `href` prefix. Rate limit: ~0.5s between calls.

**Run tests from:** `backend-fastapi/` with the project venv: `.venv/Scripts/python.exe -m pytest -q` (Windows) or `python -m pytest -q`.

---

### Task 1: Swap the audio-features source to ReccoBeats

**Files:**
- Modify: `backend-fastapi/app/config.py` (add `reccobeats_base_url`)
- Modify: `backend-fastapi/app/spotify.py:22` (drop `FEATURES_URL`), `:79-94` (`_fetch_audio_features`), `:123` (caller)
- Test: `backend-fastapi/tests/test_spotify.py` (update `test_sync_with_features_and_mood_aggregation`)

- [x] **Step 1: Update the failing test to the ReccoBeats shape**

In `tests/test_spotify.py`, replace the body of `test_sync_with_features_and_mood_aggregation` so the features mock returns ReccoBeats' `content[]` with `href`:

```python
def test_sync_with_features_and_mood_aggregation(db, monkeypatch):
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT10:00:00Z")
    monkeypatch.setattr(spotify.httpx, "post", lambda *a, **k: FakeResponse(TOKEN_PAYLOAD))

    def fake_get(url, **kwargs):
        if "recently-played" in url:
            return FakeResponse(_recent(now_iso))
        # ReccoBeats audio-features: content[] with href -> spotify id
        return FakeResponse({"content": [
            {"href": "https://open.spotify.com/track/trk1", "valence": 0.8, "energy": 0.9, "tempo": 174.0},
            {"href": "https://open.spotify.com/track/trk2", "valence": 0.4, "energy": 0.5, "tempo": 120.0},
        ]})

    monkeypatch.setattr(spotify.httpx, "get", fake_get)

    spotify.exchange_code(db, "authcode")
    spotify.sync_recently_played(db)

    summary = db.query(DailySummary).one()
    assert abs(summary.mood_valence - 0.6) < 1e-6
    assert abs(summary.mood_energy - 0.7) < 1e-6
```

(`test_sync_with_features_unavailable` needs no change — its `fake_get` returns 403 for the non-recently-played URL, which is now the ReccoBeats call; valence stays `None`.)

- [x] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_spotify.py::test_sync_with_features_and_mood_aggregation -v`
Expected: FAIL — current code posts the Spotify `audio-features` shape / passes `access_token`, so `content` is never parsed and `mood_valence` is `None`.

- [x] **Step 3: Add the config setting**

In `app/config.py`, inside `class Settings`, add (after the spotify_* block):

```python
    reccobeats_base_url: str = "https://api.reccobeats.com"
```

- [x] **Step 4: Rewrite `_fetch_audio_features` to call ReccoBeats**

In `app/spotify.py`: add `import time` at the top with the other stdlib imports; delete the `FEATURES_URL = "https://api.spotify.com/v1/audio-features"` constant (line 22); add module constants near the other URLs:

```python
RECCO_BATCH = 40
RECCO_DELAY_S = 0.5
```

Replace the whole `_fetch_audio_features` function with:

```python
def _fetch_audio_features(track_ids: list[str]) -> dict[str, dict]:
    """Best effort via ReccoBeats — Spotify's own audio-features endpoint is gone
    for apps created after Nov 2024. Returns {spotify_track_id: feature dict};
    skips any track/batch the service can't serve (valence stays NULL)."""
    if not track_ids:
        return {}
    base = get_settings().reccobeats_base_url
    out: dict[str, dict] = {}
    for i in range(0, len(track_ids), RECCO_BATCH):
        if i:
            time.sleep(RECCO_DELAY_S)  # ReccoBeats rate limit
        batch = track_ids[i:i + RECCO_BATCH]
        try:
            resp = httpx.get(f"{base}/v1/audio-features",
                             params={"ids": ",".join(batch)}, timeout=20)
            if resp.status_code != 200:
                logger.warning("ReccoBeats audio-features unavailable (HTTP %d)", resp.status_code)
                continue
            items = resp.json().get("content", [])
        except (httpx.HTTPError, ValueError, AttributeError) as e:
            logger.warning("ReccoBeats fetch failed: %s", e)
            continue
        for f in items:
            if not isinstance(f, dict):
                continue
            href = f.get("href") or ""
            sid = href.rstrip("/").rsplit("/", 1)[-1].split("?")[0] if href else None
            if sid:
                out[sid] = f
    return out
```

- [x] **Step 5: Update the caller (drop `access_token`)**

In `app/spotify.py::sync_recently_played`, change the features line (was line 123):

```python
    features = _fetch_audio_features([tid for _, tid in new_rows if tid])
```

- [x] **Step 6: Run tests to verify pass**

Run: `python -m pytest tests/test_spotify.py -v`
Expected: PASS (both `test_sync_with_features_and_mood_aggregation` and `test_sync_with_features_unavailable`).

- [x] **Step 7: Commit**

```bash
git add app/config.py app/spotify.py tests/test_spotify.py
git commit -m "feat: source audio features from ReccoBeats (Spotify audio-features is gone)"
```

---

### Task 2: Store the Spotify track id

**Files:**
- Modify: `backend-fastapi/app/models.py:78` (`ListeningSession`)
- Create: `backend-fastapi/alembic/versions/<generated>_listening_spotify_track_id.py`
- Modify: `backend-fastapi/app/spotify.py` (`sync_recently_played` row construction)
- Test: `backend-fastapi/tests/test_spotify.py` (new test)

- [x] **Step 1: Write the failing test**

Append to `tests/test_spotify.py`:

```python
def test_sync_stores_spotify_track_id(db, monkeypatch):
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT10:00:00Z")
    monkeypatch.setattr(spotify.httpx, "post", lambda *a, **k: FakeResponse(TOKEN_PAYLOAD))

    def fake_get(url, **kwargs):
        if "recently-played" in url:
            return FakeResponse(_recent(now_iso))
        return FakeResponse({"content": []})

    monkeypatch.setattr(spotify.httpx, "get", fake_get)

    spotify.exchange_code(db, "authcode")
    spotify.sync_recently_played(db)

    ids = {r.track_name: r.spotify_track_id for r in db.query(ListeningSession).all()}
    assert ids == {"Song A": "trk1", "Song B": "trk2"}
```

- [x] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_spotify.py::test_sync_stores_spotify_track_id -v`
Expected: FAIL — `ListeningSession` has no `spotify_track_id` attribute yet.

- [x] **Step 3: Add the column to the model**

In `app/models.py::ListeningSession` (after the `artist` column):

```python
    spotify_track_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
```

- [x] **Step 4: Set it during sync**

In `app/spotify.py::sync_recently_played`, add `spotify_track_id` to the `ListeningSession(...)` constructor:

```python
        row = ListeningSession(
            played_at=played_at,
            track_name=track.get("name") or "unknown",
            artist=", ".join(a.get("name", "") for a in track.get("artists", [])) or None,
            spotify_track_id=track.get("id"),
        )
```

- [x] **Step 5: Create the migration**

Run: `python -m alembic revision -m "listening spotify_track_id"` (this creates a file with the correct `down_revision` already linked to the current head). In the generated file, fill the bodies:

```python
def upgrade() -> None:
    op.add_column("listening_sessions",
                  sa.Column("spotify_track_id", sa.String(length=64), nullable=True))
    op.create_index("ix_listening_sessions_spotify_track_id",
                    "listening_sessions", ["spotify_track_id"])


def downgrade() -> None:
    op.drop_index("ix_listening_sessions_spotify_track_id",
                  table_name="listening_sessions")
    op.drop_column("listening_sessions", "spotify_track_id")
```

(Ensure `import sqlalchemy as sa` is present in the generated file — Alembic adds it by default.)

- [x] **Step 6: Run the new test AND the migration drift-guard**

Run: `python -m pytest tests/test_spotify.py::test_sync_stores_spotify_track_id tests/test_migrations.py -v`
Expected: PASS. The drift-guard (`test_migrations.py`) confirms the model column + index match the migration (no autogenerate diff). If it reports a diff, the index name in the migration must exactly equal `ix_listening_sessions_spotify_track_id`.

- [x] **Step 7: Commit**

```bash
git add app/models.py app/spotify.py alembic/versions/
git commit -m "feat: persist spotify_track_id on ListeningSession (+ migration)"
```

---

### Task 3: Give the chat the recent track list

**Files:**
- Modify: `backend-fastapi/app/chat_service.py::build_context` (lines 72-98 dict)
- Test: `backend-fastapi/tests/test_chat.py` (new test)

- [x] **Step 1: Write the failing test**

Append to `tests/test_chat.py`:

```python
def test_recent_listening_in_context(db):
    from datetime import datetime, timezone
    from app import chat_service
    from app.models import ListeningSession
    db.add(ListeningSession(
        played_at=datetime.now(timezone.utc),
        track_name="Song A", artist="Artist A",
        spotify_track_id="trk1", valence=0.8, energy=0.9))
    db.commit()

    ctx = chat_service.build_context(db)
    assert "recent_listening" in ctx
    first = ctx["recent_listening"][0]
    assert first["track"] == "Song A"
    assert first["artist"] == "Artist A"
    assert first["valence"] == 0.8
```

- [x] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_chat.py::test_recent_listening_in_context -v`
Expected: FAIL — `KeyError: 'recent_listening'`.

- [x] **Step 3: Add `recent_listening` to the snapshot**

In `app/chat_service.py::build_context`, after the existing `listening = db.scalars(...)` block, add:

```python
    recent_tracks = db.scalars(
        select(ListeningSession).order_by(ListeningSession.played_at.desc()).limit(20)
    ).all()
```

Then add this key to the returned dict (e.g. right after `"audio_priming": ...`):

```python
        "recent_listening": [
            {"day": t.played_at.date().isoformat(), "track": t.track_name,
             "artist": t.artist, "valence": t.valence, "energy": t.energy}
            for t in recent_tracks
        ],
```

(`ListeningSession` and `select` are already imported in `chat_service.py`.)

- [x] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_chat.py -v`
Expected: PASS (all chat tests).

- [x] **Step 5: Commit**

```bash
git add app/chat_service.py tests/test_chat.py
git commit -m "feat: include recent listening (tracks/artists) in chat context"
```

---

### Task 4: Backfill already-synced tracks

**Files:**
- Modify: `backend-fastapi/app/spotify.py` (add `backfill_audio_features`)
- Modify: `backend-fastapi/app/routers/integrations.py` (add `POST /spotify/backfill`)
- Test: `backend-fastapi/tests/test_spotify.py` (new test)

- [x] **Step 1: Write the failing test**

Append to `tests/test_spotify.py`:

```python
def test_backfill_populates_missing_features(db, monkeypatch):
    db.add_all([
        ListeningSession(played_at=datetime(2026, 7, 1, 10, tzinfo=timezone.utc),
                         track_name="Song A", spotify_track_id="trk1"),
        ListeningSession(played_at=datetime(2026, 7, 1, 11, tzinfo=timezone.utc),
                         track_name="Song B", spotify_track_id="trk2"),
    ])
    db.commit()

    def fake_get(url, **kwargs):
        return FakeResponse({"content": [
            {"href": "https://open.spotify.com/track/trk1", "valence": 0.8, "energy": 0.9, "tempo": 174.0},
            {"href": "https://open.spotify.com/track/trk2", "valence": 0.4, "energy": 0.5, "tempo": 120.0},
        ]})

    monkeypatch.setattr(spotify.httpx, "get", fake_get)

    assert spotify.backfill_audio_features(db) == 2
    rows = {r.track_name: r for r in db.query(ListeningSession).all()}
    assert abs(rows["Song A"].valence - 0.8) < 1e-6
    summary = db.query(DailySummary).one()
    assert summary.mood_valence is not None
```

- [x] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_spotify.py::test_backfill_populates_missing_features -v`
Expected: FAIL — `spotify.backfill_audio_features` does not exist.

- [x] **Step 3: Implement `backfill_audio_features`**

Add to `app/spotify.py` (after `aggregate_daily_mood`):

```python
def backfill_audio_features(db: Session) -> int:
    """Re-fetch ReccoBeats features for already-synced tracks that have a
    spotify_track_id but no valence. Idempotent; returns rows updated."""
    rows = db.scalars(
        select(ListeningSession).where(
            ListeningSession.spotify_track_id.is_not(None),
            ListeningSession.valence.is_(None),
        )
    ).all()
    if not rows:
        return 0
    features = _fetch_audio_features([r.spotify_track_id for r in rows])
    updated = 0
    for r in rows:
        f = features.get(r.spotify_track_id)
        if f:
            r.valence = f.get("valence")
            r.energy = f.get("energy")
            r.tempo = f.get("tempo")
            updated += 1
    db.commit()
    aggregate_daily_mood(db)
    return updated
```

- [x] **Step 4: Add the endpoint**

In `app/routers/integrations.py`, in the Spotify section (after `spotify_sync`):

```python
@router.post("/spotify/backfill", response_model=SyncResult)
def spotify_backfill(db: Session = Depends(get_db)):
    return SyncResult(synced=spotify.backfill_audio_features(db))
```

(`spotify`, `SyncResult`, `get_db`, `Depends`, `Session` are already imported.)

- [x] **Step 5: Run tests to verify pass**

Run: `python -m pytest tests/test_spotify.py::test_backfill_populates_missing_features -v`
Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add app/spotify.py app/routers/integrations.py tests/test_spotify.py
git commit -m "feat: POST /integrations/spotify/backfill to fill mood on existing tracks"
```

---

### Task 5: Full suite + rollout

- [x] **Step 1: Run the whole suite**

Run: `python -m pytest -q`
Expected: all tests PASS (the prior 75 + the new spotify/chat tests).

- [ ] **Step 2: Rollout (manual, on the Droplet — not part of the merge)**

After merging `feat/mood-reccobeats` to `main`:
```bash
ssh root@68.183.78.19
cd /srv/crux && git pull
cd backend-fastapi && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
# migration auto-runs on API startup; then backfill existing tracks once:
curl -X POST https://api.crux.com.im/integrations/spotify/backfill
```
Verify: `https://api.crux.com.im/dashboard/summary` `mood_trend` now has non-null values, and the chat answers "what have I been listening to?" with real tracks.

---

## Verification summary (gates in order)
1. Task 1 → `test_sync_with_features_and_mood_aggregation` PASS (ReccoBeats path).
2. Task 2 → `test_sync_stores_spotify_track_id` + `test_migrations` PASS (column + migration consistent).
3. Task 3 → `test_recent_listening_in_context` PASS.
4. Task 4 → `test_backfill_populates_missing_features` PASS.
5. Task 5 → `pytest -q` fully green; post-deploy `mood_trend` non-null.
