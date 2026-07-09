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
