"""Mountaineering pacing heuristics — synthetic fixtures only.
NEEDS REAL-DATA CALIBRATION before the estimates are trusted."""
from datetime import datetime, timedelta, timezone

from app.pacing import DEFAULT_FLAT_SPEED_M_S, DEFAULT_VERT_SPEED_M_H, estimate, sustained_vertical_speed
from app.models import Activity, ActivityType

T0 = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)


def _loaded(id, vert, hours):
    return Activity(id=id, source="manual", type=ActivityType.ruck,
                    start_time=T0 + timedelta(days=id), duration_s=int(hours * 3600),
                    elevation_gain_m=vert)


def _aerobic(id, pace_s_per_km):
    return Activity(id=id, source="manual", type=ActivityType.easy_run,
                    start_time=T0 + timedelta(days=id), duration_s=3600,
                    distance_m=10000, avg_pace_s_per_km=pace_s_per_km)


def test_sustained_vertical_speed_median():
    history = [_loaded(1, 600, 2), _loaded(2, 800, 2), _loaded(3, 1000, 2)]
    assert sustained_vertical_speed(history) == 400.0  # median of 300/400/500


def test_sustained_vertical_speed_empty():
    assert sustained_vertical_speed([]) is None
    # loaded sessions without vert or duration don't count
    assert sustained_vertical_speed([_loaded(1, 0, 2)]) is None


def test_estimate_personal_basis():
    history = [_loaded(1, 800, 2), _aerobic(2, 330)]  # 400 m/h; ~3.03 m/s flat
    out = estimate(distance_m=10000, elevation_gain_m=1200, history=history)
    assert out["basis"] == "personal"
    assert out["vert_speed_m_per_h"] == 400.0
    expected = 1200 / 400 * 3600 + 10000 / (1000 / 330)
    assert abs(out["est_duration_s"] - expected) < 2


def test_estimate_default_basis():
    out = estimate(distance_m=10000, elevation_gain_m=1200, history=[])
    assert out["basis"] == "default"
    assert out["vert_speed_m_per_h"] == DEFAULT_VERT_SPEED_M_H
    expected = 1200 / DEFAULT_VERT_SPEED_M_H * 3600 + 10000 / DEFAULT_FLAT_SPEED_M_S
    assert abs(out["est_duration_s"] - expected) < 2


def test_estimate_scales_with_inputs():
    small = estimate(5000, 500, [])
    big = estimate(15000, 2000, [])
    assert big["est_duration_s"] > small["est_duration_s"]


def test_estimate_endpoint(client):
    r = client.post("/pacing/estimate", json={"distance_m": 8000, "elevation_gain_m": 1000})
    assert r.status_code == 200
    body = r.json()
    assert body["basis"] == "default"  # empty DB
    assert body["est_duration_s"] > 0
    assert "calibration" in body["notes"].lower()
