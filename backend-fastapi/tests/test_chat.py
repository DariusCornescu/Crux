def test_chat_fallback_reply_and_history(client):
    # No ANTHROPIC_API_KEY in tests -> deterministic offline reply
    r = client.post("/chat", json={"message": "how was my aerobic week?"})
    assert r.status_code == 200
    assert "OFFLINE MODE" in r.json()["reply"]

    history = client.get("/chat/history").json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["content"] == "how was my aerobic week?"


def test_chat_context_reflects_data(client):
    from datetime import datetime, timezone
    client.post("/activities", json={
        "type": "easy_run", "start_time": datetime.now(timezone.utc).isoformat(),
        "duration_s": 2690, "distance_m": 8200})
    reply = client.post("/chat", json={"message": "km?"}).json()["reply"]
    assert "8.2 km aerobic" in reply


def test_history_ordering_and_limit(client):
    for i in range(3):
        client.post("/chat", json={"message": f"q{i}"})
    history = client.get("/chat/history?limit=4").json()
    assert len(history) == 4  # newest 4, oldest-first
    assert history[-1]["role"] == "assistant"
    assert history[-2]["content"] == "q2"
