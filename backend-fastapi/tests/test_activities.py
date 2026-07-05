def test_manual_sprint_entry_and_mode(client):
    r = client.post("/activities", json={
        "type": "sprint", "start_time": "2026-07-01T09:00:00Z", "duration_s": 3600,
        "splits": [7.04, 6.98, 7.02], "perceived_effort": 8, "name": "60m fly x3",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["mode"] == "explosive"
    assert body["splits"] == [7.04, 6.98, 7.02]

    r = client.get("/activities")
    assert r.status_code == 200
    assert len(r.json()) == 1
