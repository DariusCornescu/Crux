"""Training grid: dense per-day series, dominant mode, and volume."""
from datetime import date, datetime, time, timezone

from app.models import Activity, ActivityType


def test_grid_dense_dominant_mode_and_minutes(client, db):
    t = datetime.combine(date.today(), time(12, 0), tzinfo=timezone.utc)  # unambiguously today
    db.add(Activity(source="manual", type=ActivityType.easy_run, start_time=t, duration_s=3600))  # 60m aerobic
    db.add(Activity(source="manual", type=ActivityType.sprint, start_time=t, duration_s=600))      # 10m explosive
    db.commit()

    body = client.get("/training/grid?weeks=2").json()
    assert len(body["days"]) == 14                # dense two weeks
    assert body["total_sessions"] == 2
    assert body["active_days"] == 1
    today_cell = body["days"][-1]
    assert today_cell["mode"] == "aerobic"        # 60m aerobic beats 10m explosive
    assert today_cell["minutes"] == 70


def test_grid_empty(client):
    body = client.get("/training/grid?weeks=1").json()
    assert len(body["days"]) == 7
    assert body["active_days"] == 0
    assert all(d["mode"] is None for d in body["days"])
