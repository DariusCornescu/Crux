"""LLM-inferred genre per track + genre aggregation on /signals/detail."""
from datetime import datetime, timedelta, timezone

from app import genres
from app.models import ListeningSession


def _tracks(db, names):
    now = datetime.now(timezone.utc)
    for i, n in enumerate(names):
        db.add(ListeningSession(played_at=now - timedelta(hours=i + 1),
                                track_name=n, artist="A"))
    db.commit()


def test_infer_pending_offline_noop(db):
    _tracks(db, ["X", "Y"])                 # llm not configured in tests
    assert genres.infer_pending(db) == 0
    assert all(r.genre is None for r in db.query(ListeningSession).all())


def test_infer_pending_llm(db, monkeypatch):
    _tracks(db, ["Song A", "Song B"])
    monkeypatch.setattr(genres.llm, "is_configured", lambda: True)
    monkeypatch.setattr(genres.llm, "complete", lambda **k: "1. trap\n2. cloud rap\n")
    assert genres.infer_pending(db) == 2
    got = {r.track_name: r.genre for r in db.query(ListeningSession).all()}
    assert got == {"Song A": "trap", "Song B": "cloud rap"}
    assert genres.infer_pending(db) == 0    # idempotent — no NULL rows left


def test_signals_detail_genres(client, db):
    now = datetime.now(timezone.utc)
    for i, (n, g) in enumerate([("A", "trap"), ("B", "trap"), ("C", "phonk")]):
        # played_at is unique — space by a second to avoid clock-resolution collisions;
        # all three stay within the same "recent" window for the /signals/detail query.
        db.add(ListeningSession(played_at=now - timedelta(seconds=i), track_name=n, genre=g))
    db.commit()
    body = client.get("/signals/detail").json()
    counts = {row["genre"]: row["count"] for row in body["genres"]}
    assert counts == {"trap": 2, "phonk": 1}
    assert body["genres"][0]["genre"] == "trap"   # sorted desc


def test_backfill_genres_endpoint(client, db, monkeypatch):
    _tracks(db, ["Song A"])
    monkeypatch.setattr(genres.llm, "is_configured", lambda: True)
    monkeypatch.setattr(genres.llm, "complete", lambda **k: "1. phonk")
    r = client.post("/integrations/spotify/genres")
    assert r.status_code == 200 and r.json()["synced"] == 1
