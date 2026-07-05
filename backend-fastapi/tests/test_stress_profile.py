"""Hour-of-day stress profile × schedule overlay (pure functions + wiring)."""
from datetime import date, datetime, timedelta, timezone

from app import stress_profile
from app.models import CalendarEvent, DailySummary, WellnessSample

MON = datetime(2026, 6, 22, tzinfo=timezone.utc)  # Monday


def _s(day_offset, hour, value, kind="stress_score"):
    return WellnessSample(recorded_at=MON + timedelta(days=day_offset, hours=hour),
                          kind=kind, value=value, source="test")


def _meeting(day_offset, start_h, minutes, subject="x"):
    start = MON + timedelta(days=day_offset, hours=start_h)
    return CalendarEvent(start=start, end=start + timedelta(minutes=minutes),
                         subject_hash=subject, source="ics")


def _daily(day_offset, sleep_score=None, sleep_min=None, rhr=None):
    return DailySummary(day=(MON + timedelta(days=day_offset)).date(),
                        sleep_score=sleep_score, sleep_duration_min=sleep_min,
                        resting_hr=rhr)


def test_hourly_profile_buckets_workday_weekend():
    samples = [_s(0, 14, 80), _s(1, 14, 70), _s(0, 8, 40),   # workdays
               _s(5, 14, 30)]                                 # Saturday
    prof = stress_profile.hourly_profile(samples, tz_name="UTC")
    assert prof["basis"] == "stress_score"
    assert prof["workday"][14] == 75
    assert prof["workday"][8] == 40
    assert prof["weekend"][14] == 30
    assert prof["workday"][3] is None


def test_hrv_fallback_inverts():
    samples = [_s(0, 9, 90, kind="hrv_ms"), _s(0, 15, 40, kind="hrv_ms")]
    prof = stress_profile.hourly_profile(samples, tz_name="UTC")
    assert prof["basis"] == "hrv_inverted"
    assert prof["workday"][15] > prof["workday"][9]  # low HRV -> high stress


def test_stress_peak_hours_fires():
    samples = ([_s(d, 14, 85) for d in range(3)] + [_s(d, 15, 82) for d in range(3)]
               + [_s(d, 9, 45) for d in range(3)] + [_s(d, 11, 50) for d in range(3)])
    findings = stress_profile.schedule_overlay([], samples, [], tz_name="UTC")
    codes = [f["code"] for f in findings]
    assert "stress_peak_hours" in codes
    peak = next(f for f in findings if f["code"] == "stress_peak_hours")
    assert 14 in peak["evidence"]["hours"]


def test_meeting_load_correlation_fires_and_respects_threshold():
    # heavy meeting days (>=180 min): Mon/Tue with high stress; light: Wed/Thu low
    events = [_meeting(0, 9, 240, "a"), _meeting(1, 9, 200, "b"), _meeting(2, 9, 30, "c")]
    samples = ([_s(0, h, 80) for h in (10, 14)] + [_s(1, h, 78) for h in (10, 14)]
               + [_s(2, h, 50) for h in (10, 14)] + [_s(3, h, 48) for h in (10, 14)])
    findings = stress_profile.schedule_overlay(events, samples, [], tz_name="UTC")
    assert any(f["code"] == "meeting_load_correlation" for f in findings)

    flat = ([_s(0, 10, 60), _s(1, 10, 60), _s(2, 10, 60), _s(3, 10, 60)])
    findings = stress_profile.schedule_overlay(events, flat, [], tz_name="UTC")
    assert not any(f["code"] == "meeting_load_correlation" for f in findings)


def test_after_hours_meetings_sleep_fires():
    # late meetings Mon+Tue evening -> poor sleep credited to Tue+Wed mornings
    events = [_meeting(0, 19, 60, "a"), _meeting(1, 19, 60, "b")]
    dailies = [_daily(1, sleep_score=60), _daily(2, sleep_score=62),
               _daily(3, sleep_score=85), _daily(4, sleep_score=88)]
    findings = stress_profile.schedule_overlay(events, [], dailies, tz_name="UTC")
    assert any(f["code"] == "after_hours_meetings_sleep" for f in findings)


def test_morning_meeting_rhr_fires():
    events = [_meeting(0, 8, 60, "a"), _meeting(1, 8, 30, "b"), _meeting(2, 11, 60, "c")]
    dailies = [_daily(0, rhr=58), _daily(1, rhr=57), _daily(2, rhr=52), _daily(3, rhr=51)]
    findings = stress_profile.schedule_overlay(events, [], dailies, tz_name="UTC")
    assert any(f["code"] == "morning_meeting_rhr" for f in findings)


def test_endpoint_chat_and_report_wiring(client, db):
    now = datetime.now(timezone.utc)
    client.post("/wellness/ingest", json={"samples": [
        {"recorded_at": (now - timedelta(hours=2)).isoformat(), "kind": "stress_score",
         "value": 70, "source": "test"}]})

    r = client.get("/insights/stress-profile")
    assert r.status_code == 200
    body = r.json()
    assert {"window_days", "hourly", "findings", "meeting_load"} <= set(body)

    from app.chat_service import build_context
    assert "stress_profile" in build_context(db)

    from app.report_generator import build_week_summary
    monday = date.today() - timedelta(days=date.today().weekday())
    summary = build_week_summary(db, monday, monday + timedelta(days=6))
    assert "schedule_stress" in summary
