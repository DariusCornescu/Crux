from datetime import datetime, timedelta, timezone

from app import spotify
from app.models import DailySummary, ListeningSession
from tests.conftest import FakeResponse

TOKEN_PAYLOAD = {"access_token": "at1", "refresh_token": "rt1", "expires_in": 3600,
                 "scope": "user-read-recently-played"}


def _recent(now_iso):
    return {"items": [
        {"played_at": now_iso,
         "track": {"id": "trk1", "name": "Song A", "artists": [{"name": "Artist A"}]}},
        {"played_at": now_iso.replace("T10", "T11"),
         "track": {"id": "trk2", "name": "Song B", "artists": [{"name": "Artist B"}]}},
    ]}


def test_sync_with_features_unavailable(db, monkeypatch):
    """Spotify restricted audio-features for new apps — sync must still work."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT10:00:00Z")
    monkeypatch.setattr(spotify.httpx, "post", lambda *a, **k: FakeResponse(TOKEN_PAYLOAD))

    def fake_get(url, **kwargs):
        if "recently-played" in url:
            return FakeResponse(_recent(now_iso))
        return FakeResponse({"error": "forbidden"}, status_code=403)

    monkeypatch.setattr(spotify.httpx, "get", fake_get)

    spotify.exchange_code(db, "authcode")
    assert spotify.sync_recently_played(db) == 2
    assert spotify.sync_recently_played(db) == 0  # idempotent on played_at

    rows = db.query(ListeningSession).all()
    assert len(rows) == 2
    assert all(r.valence is None for r in rows)


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


def test_fetch_audio_features_batches_and_merges(monkeypatch):
    calls = []
    sleeps = []
    monkeypatch.setattr(spotify.time, "sleep", lambda s: sleeps.append(s))

    def fake_get(url, params=None, **kwargs):
        ids = params["ids"].split(",")
        calls.append(len(ids))
        return FakeResponse({"content": [
            {"href": f"https://open.spotify.com/track/{i}", "valence": 0.5} for i in ids
        ]})

    monkeypatch.setattr(spotify.httpx, "get", fake_get)

    out = spotify._fetch_audio_features([f"t{n}" for n in range(41)])
    assert calls == [40, 1]          # split into two batches
    assert sleeps == [spotify.RECCO_DELAY_S]  # one sleep, between batches only
    assert len(out) == 41            # results merged across batches


def test_fetch_audio_features_survives_malformed_200(monkeypatch):
    class BadJson:
        status_code = 200
        def json(self):
            raise ValueError("not json")
    monkeypatch.setattr(spotify.httpx, "get", lambda *a, **k: BadJson())
    assert spotify._fetch_audio_features(["t1"]) == {}


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


def test_backfill_populates_missing_features(db, monkeypatch):
    # Inside the 14-day mood window; mid-day so base+1h stays on the same day.
    base = (datetime.now(timezone.utc) - timedelta(days=2)).replace(hour=10, minute=0)
    db.add_all([
        ListeningSession(played_at=base, track_name="Song A", spotify_track_id="trk1"),
        ListeningSession(played_at=base + timedelta(hours=1),
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


def test_fetch_audio_features_survives_null_content(monkeypatch):
    monkeypatch.setattr(spotify.httpx, "get",
                        lambda *a, **k: FakeResponse({"content": None}))
    assert spotify._fetch_audio_features(["t1"]) == {}
