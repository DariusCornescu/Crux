def test_status_disconnected(client):
    s = client.get("/integrations/status").json()
    assert s["strava"]["connected"] is False
    assert s["spotify"]["connected"] is False


def test_sync_requires_connection(client):
    assert client.post("/integrations/strava/sync").status_code == 400


def test_authorize_urls(client):
    assert "strava.com/oauth/authorize" in client.get("/integrations/strava/authorize").json()["authorize_url"]
    assert "accounts.spotify.com/authorize" in client.get("/integrations/spotify/authorize").json()["authorize_url"]
