"""Summit objective: upsert (single active), current with computed banked + days,
and vertical banked summing only activities since start_date."""
from datetime import date, datetime, timezone

from app import objective
from app.models import Activity, ActivityType, Objective


def test_no_objective_returns_null(client):
    assert client.get("/objective/current").json() is None


def test_upsert_current_and_single_active(client, db):
    r = client.post("/objective", json={"name": "Mont Blanc", "elevation_m": 4808,
                                        "target_date": "2026-09-30", "vert_goal_m": 30000})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Mont Blanc" and body["vert_goal_m"] == 30000
    assert "banked_m" in body and "days_to_go" in body

    assert client.get("/objective/current").json()["name"] == "Mont Blanc"

    client.post("/objective", json={"name": "Matterhorn", "target_date": "2026-10-15",
                                    "vert_goal_m": 40000})
    assert db.query(Objective).count() == 1                       # updated, not duplicated
    assert client.get("/objective/current").json()["name"] == "Matterhorn"


def test_banked_vert_sums_since_start(db):
    obj = objective.upsert(db, name="Peak", target_date=date(2026, 12, 1),
                           vert_goal_m=10000, start_date=date(2026, 7, 1))
    db.add(Activity(source="manual", type=ActivityType.hike,
                    start_time=datetime(2026, 7, 5, tzinfo=timezone.utc),
                    duration_s=3600, elevation_gain_m=800))
    db.add(Activity(source="manual", type=ActivityType.hike,
                    start_time=datetime(2026, 6, 20, tzinfo=timezone.utc),  # before start -> excluded
                    duration_s=3600, elevation_gain_m=500))
    db.commit()
    assert objective.banked_m(db, obj) == 800
