"""Readiness: LOW DATA without wearable signals, READY/REST bands with them."""
from datetime import date

from app.models import DailySummary


def test_low_data_without_summary(client):
    body = client.get("/readiness/today").json()
    assert body["low_data"] is True and body["label"] == "LOW DATA"


def test_ready_with_good_recovery(client, db):
    db.add(DailySummary(day=date.today(), sleep_duration_min=480, resting_hr=48, training_load=20))
    db.commit()
    body = client.get("/readiness/today").json()
    assert body["low_data"] is False
    assert body["score"] >= 67 and body["label"] == "READY"
    assert body["sleep_min"] == 480 and body["resting_hr"] == 48


def test_rest_with_poor_recovery(client, db):
    db.add(DailySummary(day=date.today(), sleep_duration_min=300, resting_hr=70, training_load=90))
    db.commit()
    body = client.get("/readiness/today").json()
    assert body["low_data"] is False
    assert body["label"] in ("REST", "EASY")     # depressed score
