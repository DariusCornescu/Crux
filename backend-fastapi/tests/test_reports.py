from datetime import date, datetime, timedelta, timezone


def _seed_week(client):
    monday = date.today() - timedelta(days=date.today().weekday() + 7)
    base = datetime.combine(monday, datetime.min.time(), tzinfo=timezone.utc)
    client.post("/activities", json={
        "type": "sprint", "start_time": (base + timedelta(days=0, hours=9)).isoformat(),
        "duration_s": 3600, "splits": [7.04, 6.98, 7.02], "perceived_effort": 8})
    client.post("/activities", json={
        "type": "easy_run", "start_time": (base + timedelta(days=1, hours=6)).isoformat(),
        "duration_s": 2690, "distance_m": 8200, "avg_pace_s_per_km": 328})
    client.post("/activities", json={
        "type": "ruck", "start_time": (base + timedelta(days=2, hours=7)).isoformat(),
        "duration_s": 5400, "elevation_gain_m": 540, "load_kg": 18})
    return monday


def test_generate_fallback_report(client):
    monday = _seed_week(client)

    r = client.post("/reports/generate", json={})
    assert r.status_code == 200
    report = r.json()
    assert report["kind"] == "weekly"
    assert report["period_start"] == monday.isoformat()
    for section in ("## Gate", "## Strip", "## Alti", "## Recovery & Mood"):
        assert section in report["body_md"]
    assert "8.2 km" in report["body_md"]
    assert report["highlights"]["headline"]

    # Regenerating the same week replaces, not duplicates
    client.post("/reports/generate", json={})
    assert len(client.get("/reports").json()) == 1

    detail = client.get(f"/reports/{report['id']}")
    assert detail.status_code == 200
    assert client.get("/reports/999").status_code == 404


def test_week_summary_includes_subjective_block(client, db):
    monday = _seed_week(client)
    log_day = datetime.combine(monday + timedelta(days=3),
                               datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=9)
    client.post("/voice-logs", json={"transcript": "picioare grele azi",
                                     "created_at": log_day.isoformat()})

    from app.report_generator import build_week_summary
    summary = build_week_summary(db, monday, monday + timedelta(days=6))
    assert len(summary["subjective"]) == 1
    entry = summary["subjective"][0]
    assert entry["symptoms"] == ["heavy_legs"]
    assert entry["day"] == (monday + timedelta(days=3)).isoformat()
    assert "subjective_flags" in summary

    # Fallback report mentions the subjective data
    report = client.post("/reports/generate", json={}).json()
    assert "Subjective" in report["body_md"]


def test_report_metrics_shape_and_days(client, db):
    # generate() with no week_start defaults to the last FULL Monday-Sunday
    # week (see report_generator.week_bounds), not the current in-progress
    # week — so the activity must land inside that previous week for the
    # km assertion below to be deterministic.
    monday = date.today() - timedelta(days=date.today().weekday() + 7)
    activity_time = datetime.combine(
        monday, datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1, hours=9)
    client.post("/activities", json={
        "type": "easy_run", "start_time": activity_time.isoformat(),
        "duration_s": 2400, "distance_m": 8000})
    client.post("/reports/generate", json={})
    rep = client.get("/reports").json()[0]

    r = client.get(f"/reports/{rep['id']}/metrics")
    assert r.status_code == 200
    days = r.json()["days"]
    assert len(days) == 7
    assert set(days[0]) >= {"day", "km", "vert_m", "mood_valence", "sessions"}
    assert any(abs(d["km"] - 8.0) < 1e-6 for d in days)
    assert client.get("/reports/9999/metrics").status_code == 404
