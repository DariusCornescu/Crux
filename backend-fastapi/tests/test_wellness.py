"""Wearable sample ingestion + daily roll-up into DailySummary."""
from datetime import datetime, time, timedelta, timezone

# Anchor samples to a fixed hour of TODAY (UTC) so `hours_ago` offsets never
# cross the UTC midnight boundary — `now() - 9h` did, splitting the roll-up
# across two DailySummary rows whenever the suite ran before 09:00 UTC.
_ANCHOR = datetime.combine(datetime.now(timezone.utc).date(),
                           time(hour=23, tzinfo=timezone.utc))


def _sample(kind, value, hours_ago=1, source="health_connect"):
    return {
        "recorded_at": (_ANCHOR - timedelta(hours=hours_ago)).isoformat(),
        "kind": kind, "value": value, "source": source,
    }


def test_ingest_batch_idempotent(client):
    batch = {"samples": [
        _sample("resting_hr", 52, hours_ago=3),
        _sample("stress_score", 61, hours_ago=2),
        _sample("hrv_ms", 74, hours_ago=1),
    ]}
    r = client.post("/wellness/ingest", json=batch)
    assert r.status_code == 200
    assert r.json() == {"ingested": 3, "duplicates": 0}

    r = client.post("/wellness/ingest", json=batch)
    assert r.json() == {"ingested": 0, "duplicates": 3}


def test_ingest_rejects_unknown_kind(client):
    r = client.post("/wellness/ingest", json={"samples": [_sample("moon_phase", 0.5)]})
    assert r.status_code == 422


def test_rollup_fills_daily_summary(client, db):
    from app.models import DailySummary

    client.post("/wellness/ingest", json={"samples": [
        _sample("sleep_minutes", 400, hours_ago=9),   # main sleep
        _sample("sleep_minutes", 32, hours_ago=5),    # nap — sums
        _sample("sleep_score", 82, hours_ago=9),
        _sample("resting_hr", 54, hours_ago=8),
        _sample("resting_hr", 50, hours_ago=4),       # avg -> 52
        _sample("steps", 6000, hours_ago=6),          # earlier partial total
        _sample("steps", 9500, hours_ago=2),          # later total — MAX wins
    ]})
    summary = db.query(DailySummary).one()
    assert summary.sleep_duration_min == 432
    assert summary.sleep_score == 82
    assert summary.resting_hr == 52
    assert summary.steps == 9500


def test_conditions_strip_shows_wearable_data(client):
    from datetime import datetime, timezone
    client.post("/wellness/ingest", json={"samples": [
        _sample("sleep_minutes", 432, hours_ago=9),
        _sample("resting_hr", 52, hours_ago=8),
        _sample("steps", 8241, hours_ago=2),
    ]})
    # real-data path needs an activity
    client.post("/activities", json={
        "type": "easy_run", "start_time": datetime.now(timezone.utc).isoformat(),
        "duration_s": 2400, "distance_m": 8000})
    d = client.get("/dashboard/summary").json()
    assert d["conditions"]["sleep_min"] == 432
    assert d["conditions"]["resting_hr"] == 52
    assert d["conditions"]["steps"] == 8241
