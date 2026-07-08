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
