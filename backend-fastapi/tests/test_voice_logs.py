"""POST /voice-logs + GET /voice-logs, incl. same-day Activity linkage."""
from datetime import datetime, timedelta, timezone


def test_post_extracts_and_links_same_day_activity(client):
    now = datetime.now(timezone.utc)
    r = client.post("/activities", json={
        "type": "sprint", "start_time": now.isoformat(), "duration_s": 3600,
        "splits": [7.01, 6.99]})
    activity_id = r.json()["id"]

    r = client.post("/voice-logs", json={"transcript": "RPE 9, picioare grele după sprinturi"})
    assert r.status_code == 201
    log = r.json()
    assert log["perceived_effort"] == 9
    assert log["session_type"] == "sprint"
    assert log["extraction_method"] == "deterministic"
    assert log["activity_id"] == activity_id
    assert "heavy_legs" in log["extracted"]["symptoms"]

    listed = client.get("/voice-logs").json()
    assert len(listed) == 1 and listed[0]["id"] == log["id"]


def test_post_explicit_activity_id_wins(client):
    now = datetime.now(timezone.utc)
    a1 = client.post("/activities", json={
        "type": "easy_run", "start_time": (now - timedelta(days=3)).isoformat(),
        "duration_s": 2400, "distance_m": 8000}).json()["id"]
    client.post("/activities", json={
        "type": "hike", "start_time": now.isoformat(), "duration_s": 5400})

    r = client.post("/voice-logs", json={"transcript": "tempo 6/10", "activity_id": a1})
    assert r.json()["activity_id"] == a1


def test_post_without_same_day_activity_links_null(client):
    r = client.post("/voice-logs", json={"transcript": "easy run 5/10"})
    assert r.status_code == 201
    assert r.json()["activity_id"] is None


def test_list_newest_first(client):
    old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    client.post("/voice-logs", json={"transcript": "ruck 7/10", "created_at": old})
    client.post("/voice-logs", json={"transcript": "sprint 9/10"})
    listed = client.get("/voice-logs").json()
    assert len(listed) == 2
    assert listed[0]["session_type"] == "sprint"  # newest first
