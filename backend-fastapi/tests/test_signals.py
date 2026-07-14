from datetime import datetime, timedelta, timezone

from app.models import DailySummary, ListeningSession


def test_signals_detail_shape_and_order(client, db):
    now = datetime.now(timezone.utc)
    db.add_all([
        ListeningSession(played_at=now - timedelta(hours=2), track_name="Older", valence=0.4),
        ListeningSession(played_at=now, track_name="Newest", artist="A", valence=0.8, energy=0.9),
    ])
    db.add(DailySummary(day=now.date(), sleep_duration_min=432, resting_hr=52, steps=8241, mood_valence=0.5))
    db.commit()

    r = client.get("/signals/detail")
    assert r.status_code == 200
    body = r.json()
    tracks = body["recent_tracks"]
    assert [t["track"] for t in tracks] == ["Newest", "Older"]
    assert set(tracks[0]) >= {"played_at", "track", "artist", "valence", "energy"}
    daily = body["daily"]
    assert daily[0]["sleep_min"] == 432 and daily[0]["resting_hr"] == 52
    assert daily[0]["steps"] == 8241
