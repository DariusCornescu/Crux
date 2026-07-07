def test_demo_payload_when_empty(client):
    d = client.get("/dashboard/summary").json()
    assert d["demo"] is True
    assert d["gate"]["best_split"] == 6.98
    assert d["gate"]["pb"] == 6.91
    assert len(d["mood_trend"]) == 14
    assert len(d["rail"]) == 6


def test_real_path_after_data(client):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    client.post("/activities", json={
        "type": "ruck", "start_time": now, "duration_s": 5400,
        "elevation_gain_m": 540, "load_kg": 18,
    })
    d = client.get("/dashboard/summary").json()
    assert d["demo"] is False
    assert d["alti"]["vert_m"] == 540
    assert d["alti"]["load_kg"] == 18
    assert d["alti"]["carries"] == 1
    assert d["gate"]["best_split"] is None  # no demo bleed-through
    assert len(d["mood_trend"]) == 14
