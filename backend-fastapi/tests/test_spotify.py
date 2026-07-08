from datetime import datetime, timezone

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
