"""Daily quote: curated + attributed, cached per day, archive, lens rotation."""
from datetime import date, timedelta

from app import quotes
from app.models import DailyQuote


def test_quote_today_curated_and_cached(db):
    q1 = quotes.get_today(db)
    assert q1.source == "curated" and q1.text and q1.author
    q2 = quotes.get_today(db)
    assert q2.id == q1.id                  # cached, no duplicate row
    assert db.query(DailyQuote).count() == 1


def test_quote_matches_curated_rotation(db):
    q = quotes.get_today(db)
    idx = date.today().timetuple().tm_yday % len(quotes.CURATED)
    exp_text, exp_author = quotes.CURATED[idx]
    assert q.text == exp_text and q.author == exp_author


def test_quote_endpoint(client):
    r = client.get("/quote/today")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"day", "text", "source", "author"}
    assert body["text"] and body["author"]


def test_quote_archive_newest_first_and_limit(client, db):
    for i in range(3):
        db.add(DailyQuote(day=date(2026, 7, 10) + timedelta(days=i), text=f"q{i}",
                          source="curated", author=f"a{i}"))
    db.commit()

    r = client.get("/quote/archive?limit=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2                       # limit respected
    assert body[0]["day"] >= body[1]["day"]     # newest first
    assert body[0]["text"] == "q2" and body[0]["author"] == "a2"


def test_quote_archive_empty_ok(client):
    r = client.get("/quote/archive")
    assert r.status_code == 200
    assert r.json() == []


def test_lens_rotates_by_day():
    d = date(2026, 7, 14)
    assert quotes.lens_for(d) in quotes.LENSES
    assert quotes.lens_for(d) != quotes.lens_for(d + timedelta(days=1))       # consecutive differ
    assert quotes.lens_for(d) == quotes.lens_for(d + timedelta(days=len(quotes.LENSES)))  # cycles


def test_curated_all_attributed():
    assert len(quotes.CURATED) >= 12
    for text, author in quotes.CURATED:
        assert text and author
