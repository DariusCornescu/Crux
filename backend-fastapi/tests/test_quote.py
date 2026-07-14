"""Daily quote: static fallback offline, cached per day, endpoint shape."""
from app import quotes
from app.models import DailyQuote


def test_quote_today_static_fallback_and_cached(db):
    q1 = quotes.get_today(db)          # llm not configured in tests -> static
    assert q1.source == "static" and q1.text
    q2 = quotes.get_today(db)
    assert q2.id == q1.id              # cached, no duplicate row
    assert db.query(DailyQuote).count() == 1


def test_quote_endpoint(client):
    r = client.get("/quote/today")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"day", "text", "source"}
    assert body["text"]


def test_quote_llm_branch_and_failure_fallback(db, monkeypatch):
    from app import quotes

    monkeypatch.setattr(quotes.llm, "is_configured", lambda: True)
    monkeypatch.setattr(quotes.llm, "complete", lambda **k: ' "Go far." ')
    q = quotes.get_today(db)
    assert q.source == "llm" and q.text == "Go far."   # stripped quotes/whitespace


def test_quote_llm_failure_falls_back_static(db, monkeypatch):
    from app import quotes

    monkeypatch.setattr(quotes.llm, "is_configured", lambda: True)
    def boom(**k):
        raise RuntimeError("provider down")
    monkeypatch.setattr(quotes.llm, "complete", boom)
    q = quotes.get_today(db)
    assert q.source == "static" and q.text


def test_quote_archive_newest_first_and_limit(client, db):
    from datetime import date, timedelta

    for i in range(3):
        db.add(DailyQuote(day=date(2026, 7, 10) + timedelta(days=i), text=f"q{i}", source="static"))
    db.commit()

    r = client.get("/quote/archive?limit=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2                       # limit respected
    assert body[0]["day"] >= body[1]["day"]     # newest first
    assert body[0]["text"] == "q2"


def test_quote_archive_empty_ok(client):
    r = client.get("/quote/archive")
    assert r.status_code == 200
    assert r.json() == []


def test_lens_rotates_by_day():
    from datetime import date, timedelta

    from app import quotes

    d = date(2026, 7, 14)
    assert quotes.lens_for(d) in quotes.LENSES
    assert quotes.lens_for(d) != quotes.lens_for(d + timedelta(days=1))   # consecutive days differ
    assert quotes.lens_for(d) == quotes.lens_for(d)                       # deterministic
    assert quotes.lens_for(d) == quotes.lens_for(d + timedelta(days=len(quotes.LENSES)))  # cycles
