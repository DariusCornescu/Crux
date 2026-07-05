"""Deterministic subjective<->objective cross-references (pure functions)."""
from datetime import datetime, timedelta, timezone

from app.correlations import subjective_flags
from app.models import Activity, ActivityType, VoiceLog

MONDAY = datetime(2026, 6, 22, 8, 0, tzinfo=timezone.utc)


def _ruck(vert: float) -> Activity:
    return Activity(id=1, source="manual", type=ActivityType.ruck,
                    start_time=MONDAY, duration_s=5400, elevation_gain_m=vert)


def _heavy_legs_log(days_after: int) -> VoiceLog:
    return VoiceLog(id=10, created_at=MONDAY + timedelta(days=days_after, hours=2),
                    transcript="picioare grele", extraction_method="deterministic",
                    extracted={"symptoms": ["heavy_legs"], "terrain": []})


def test_flag_fires_next_day_after_big_vert():
    flags = subjective_flags([_ruck(900)], [_heavy_legs_log(days_after=1)])
    assert len(flags) == 1
    flag = flags[0]
    assert flag["code"] == "heavy_legs_after_big_vert"
    assert "900" in flag["message"]
    assert flag["evidence"]["activity_id"] == 1


def test_flag_fires_same_day():
    assert len(subjective_flags([_ruck(900)], [_heavy_legs_log(days_after=0)])) == 1


def test_no_flag_below_vert_threshold():
    assert subjective_flags([_ruck(400)], [_heavy_legs_log(days_after=1)]) == []


def test_no_flag_two_days_later():
    assert subjective_flags([_ruck(900)], [_heavy_legs_log(days_after=2)]) == []


def test_no_flag_without_heavy_legs():
    log = _heavy_legs_log(1)
    log.extracted = {"symptoms": ["strong"], "terrain": []}
    assert subjective_flags([_ruck(900)], [log]) == []
