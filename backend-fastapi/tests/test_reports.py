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

