from datetime import datetime, timedelta, timezone

from app import strava
from app.models import Activity, ActivityType
from tests.conftest import FakeResponse

TOKEN_PAYLOAD = {
    "access_token": "at1", "refresh_token": "rt1",
    "expires_at": int((datetime.now(timezone.utc) + timedelta(hours=6)).timestamp()),
    "athlete": {"id": 12345},
}

ACTIVITIES = [
    {"id": 1001, "sport_type": "Run", "name": "Morning easy", "distance": 8200.0,
     "moving_time": 2690, "start_date": "2026-06-30T06:10:00Z", "total_elevation_gain": 40.0,
     "average_heartrate": 141.0},
    {"id": 1002, "sport_type": "Hike", "name": "Ruck 18kg forest", "distance": 6500.0,
     "moving_time": 5400, "start_date": "2026-07-01T07:00:00Z", "total_elevation_gain": 540.0},
    {"id": 1003, "sport_type": "Run", "name": "Tempo 4k", "distance": 4000.0,
     "moving_time": 1080, "start_date": "2026-07-02T18:00:00Z", "total_elevation_gain": 10.0},
]


def test_classify():
    assert strava.classify("Run", "Morning easy") == ActivityType.easy_run
    assert strava.classify("Run", "Tempo 4k") == ActivityType.tempo
    assert strava.classify("Hike", "Ruck 18kg forest") == ActivityType.ruck
    assert strava.classify("Hike", "Sunday summit") == ActivityType.hike
    assert strava.classify("WeightTraining", "Gym") == ActivityType.strength
    assert strava.classify("Run", "Sprint gate work") == ActivityType.sprint


def test_exchange_and_sync_idempotent(db, monkeypatch):
    monkeypatch.setattr(strava.httpx, "post", lambda *a, **k: FakeResponse(TOKEN_PAYLOAD))
    monkeypatch.setattr(strava.httpx, "get", lambda *a, **k: FakeResponse(ACTIVITIES))

    token = strava.exchange_code(db, "authcode")
    assert token.athlete_id == "12345"

    assert strava.sync_activities(db) == 3
    assert strava.sync_activities(db) == 3  # second run updates, not duplicates
    assert db.query(Activity).count() == 3

    ruck = db.query(Activity).filter(Activity.external_id == "1002").one()
    assert ruck.type == ActivityType.ruck
    assert ruck.elevation_gain_m == 540.0

    easy = db.query(Activity).filter(Activity.external_id == "1001").one()
    assert easy.avg_pace_s_per_km == 2690 / 8.2


def test_sync_without_connection_raises(db):
    import pytest
    with pytest.raises(RuntimeError):
        strava.sync_activities(db)
