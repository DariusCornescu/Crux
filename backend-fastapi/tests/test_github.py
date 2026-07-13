"""GitHub contribution sync (graphql + public-events + graceful degrade), the
heatmap math (dense fill, total, streaks), and integrations status/sync."""
from datetime import datetime, timedelta, timezone

import pytest

from app import github
from app.config import get_settings
from app.models import DailyContribution, OAuthToken
from tests.conftest import FakeResponse


@pytest.fixture
def gh_public(monkeypatch):
    monkeypatch.setenv("GITHUB_USERNAME", "octocat")
    monkeypatch.setenv("GITHUB_TOKEN", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def gh_token(monkeypatch):
    monkeypatch.setenv("GITHUB_USERNAME", "octocat")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_sync_graphql_parses_per_day(db, monkeypatch, gh_token):
    payload = {"data": {"user": {"contributionsCollection": {"contributionCalendar": {
        "weeks": [
            {"contributionDays": [
                {"date": "2026-07-10", "contributionCount": 3},
                {"date": "2026-07-11", "contributionCount": 0},
            ]},
            {"contributionDays": [
                {"date": "2026-07-12", "contributionCount": 5},
            ]},
        ]
    }}}}}
    monkeypatch.setattr(github.httpx, "post", lambda *a, **k: FakeResponse(json_data=payload))

    assert github.sync(db) == 3
    rows = {r.day.isoformat(): r for r in db.query(DailyContribution).all()}
    assert rows["2026-07-10"].count == 3
    assert rows["2026-07-12"].count == 5
    assert all(r.source == "graphql" for r in rows.values())


def test_sync_public_events_buckets_by_day(db, monkeypatch, gh_public):
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    events = [{"created_at": stamp}, {"created_at": stamp}]
    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        return FakeResponse(json_data=events if calls["n"] == 1 else [])

    monkeypatch.setattr(github.httpx, "get", fake_get)

    assert github.sync(db) == 1                 # both events land on the same day
    row = db.query(DailyContribution).one()
    assert row.count == 2 and row.source == "events"


def test_sync_degrades_on_http_error(db, monkeypatch, gh_public):
    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(github.httpx, "get", boom)

    assert github.sync(db) == 0                 # degrades, does not raise
    assert db.query(DailyContribution).count() == 0
    # connection registry row is still written, so the app shows "connected"
    assert db.query(OAuthToken).filter_by(provider="github").count() == 1


def test_sync_unconfigured_raises(db):
    get_settings.cache_clear()
    with pytest.raises(RuntimeError):
        github.sync(db)


def test_heatmap_dense_fill_total_and_streaks(client, db):
    today = datetime.now(timezone.utc).date()
    for delta, count in [(0, 2), (1, 1), (2, 4), (5, 3)]:
        db.add(DailyContribution(day=today - timedelta(days=delta), count=count, source="graphql"))
    db.commit()

    body = client.get("/github/heatmap?weeks=2").json()
    assert len(body["days"]) == 14                  # dense zero-filled two weeks
    assert body["total"] == 2 + 1 + 4 + 3
    assert body["current_streak"] == 3              # today, -1, -2
    assert body["longest_streak"] == 3
    assert body["source"] == "graphql"


def test_heatmap_empty_ok(client):
    body = client.get("/github/heatmap?weeks=1").json()
    assert len(body["days"]) == 7
    assert body["total"] == 0
    assert body["current_streak"] == 0
    assert body["source"] == "none"


def test_status_reports_github(client, gh_public):
    s = client.get("/integrations/status").json()
    assert s["github"]["connected"] is True
    assert s["github"]["athlete_id"] == "octocat"


def test_status_github_unconfigured(client):
    get_settings.cache_clear()
    assert client.get("/integrations/status").json()["github"]["connected"] is False


def test_github_sync_endpoint_unconfigured_400(client):
    get_settings.cache_clear()
    assert client.post("/integrations/github/sync").status_code == 400
