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


def test_recent_listening_in_context(db):
    from datetime import datetime, timezone
    from app import chat_service
    from app.models import ListeningSession
    db.add(ListeningSession(
        played_at=datetime.now(timezone.utc),
        track_name="Song A", artist="Artist A",
        spotify_track_id="trk1", valence=0.8, energy=0.9))
    db.commit()

    ctx = chat_service.build_context(db)
    assert "recent_listening" in ctx
    first = ctx["recent_listening"][0]
    assert first["track"] == "Song A"
    assert first["artist"] == "Artist A"
    assert first["valence"] == 0.8


def test_recent_listening_ignores_window_and_orders_newest_first(db):
    from datetime import datetime, timedelta, timezone
    from app import chat_service
    from app.models import ListeningSession
    old = datetime.now(timezone.utc) - timedelta(days=60)   # outside the 28d window
    new = datetime.now(timezone.utc)
    db.add_all([
        ListeningSession(played_at=old, track_name="Old Song"),
        ListeningSession(played_at=new, track_name="New Song"),
    ])
    db.commit()

    tracks = [t["track"] for t in chat_service.build_context(db)["recent_listening"]]
    assert tracks == ["New Song", "Old Song"]  # newest first, old row still present


def test_clear_history(client):
    client.post("/chat", json={"message": "hello"})
    r = client.delete("/chat/history")
    assert r.status_code == 200 and r.json()["deleted"] == 2
    assert client.get("/chat/history").json() == []
    assert client.delete("/chat/history").json()["deleted"] == 0


def test_chat_stream_offline_sse(client):
    with client.stream("POST", "/chat/stream", json={"message": "km this week?"}) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        lines = [ln for ln in r.iter_lines() if ln]
    assert lines[-1] == "data: [DONE]"
    import json as _json
    tokens = [_json.loads(ln[6:])["t"] for ln in lines[:-1] if ln.startswith("data: ")]
    assert "OFFLINE MODE" in "".join(tokens)
    history = client.get("/chat/history").json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert "OFFLINE MODE" in history[-1]["content"]


def test_chat_stream_midfailure_persists_partial(client, monkeypatch):
    from app import chat_service

    def fake_stream(**k):
        yield "Half"
        raise RuntimeError("provider died")
    monkeypatch.setattr(chat_service.llm, "is_configured", lambda: True)
    monkeypatch.setattr(chat_service.llm, "stream", fake_stream)

    with client.stream("POST", "/chat/stream", json={"message": "q"}) as r:
        lines = [ln for ln in r.iter_lines() if ln]
    assert lines[-1] == "data: [DONE]"
    history = client.get("/chat/history").json()
    assert history[-1]["role"] == "assistant"
    assert history[-1]["content"].startswith("Half") and "SIGNAL LOST" in history[-1]["content"]


def test_stream_message_persists_on_generator_close(db, monkeypatch):
    from app import chat_service
    from app.models import ChatMessage

    def fake_stream(**k):
        yield "Tok1"
        yield "Tok2"
        yield "Tok3"
    monkeypatch.setattr(chat_service.llm, "is_configured", lambda: True)
    monkeypatch.setattr(chat_service.llm, "stream", fake_stream)

    gen = chat_service.stream_message(db, "q")
    assert next(gen) == "Tok1"
    gen.close()  # simulates client disconnect (GeneratorExit)

    rows = db.query(ChatMessage).order_by(ChatMessage.id).all()
    assert [r.role for r in rows] == ["user", "assistant"]
    assert rows[-1].content == "Tok1 — [interrupted]"
