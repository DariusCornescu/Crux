"""Daily reflection: static fallback offline, cached per day, endpoint shape,
and the pre-warm task that populates mood + quote + reflection together."""
from app import reflection
from app.models import DailyMood, DailyQuote, DailyReflection


def test_reflection_static_fallback_and_cached(db):
    r1 = reflection.get_today(db)          # llm not configured in tests -> static fallback
    assert r1.source == "static" and r1.text
    r2 = reflection.get_today(db)
    assert r2.id == r1.id                  # cached, no duplicate row
    assert db.query(DailyReflection).count() == 1


def test_reflection_endpoint(client):
    r = client.get("/reflection/today")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"day", "text", "source"}
    assert body["text"]


def test_reflection_llm_branch(db, monkeypatch):
    monkeypatch.setattr(reflection.llm, "is_configured", lambda: True)
    monkeypatch.setattr(reflection.llm, "complete", lambda **k: '  "Steady base, quiet mind."  ')
    r = reflection.get_today(db)
    assert r.source == "llm" and r.text == "Steady base, quiet mind."   # stripped quotes/space


def test_reflection_llm_failure_falls_back(db, monkeypatch):
    monkeypatch.setattr(reflection.llm, "is_configured", lambda: True)

    def boom(**k):
        raise RuntimeError("provider down")

    monkeypatch.setattr(reflection.llm, "complete", boom)
    r = reflection.get_today(db)
    assert r.source == "static" and r.text


def test_prewarm_philosophy_populates_all(db):
    from app.workers.tasks import prewarm_philosophy

    prewarm_philosophy()   # runs synchronously; llm unconfigured -> deterministic fallbacks
    assert db.query(DailyMood).count() == 1
    assert db.query(DailyQuote).count() == 1
    assert db.query(DailyReflection).count() == 1
