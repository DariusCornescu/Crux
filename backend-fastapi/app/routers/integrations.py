"""OAuth flows for Strava (step 2) and Spotify (step 4). Skeleton stubs."""
from urllib.parse import urlencode

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/strava/authorize")
def strava_authorize() -> dict:
    s = get_settings()
    params = urlencode({
        "client_id": s.strava_client_id,
        "redirect_uri": s.strava_redirect_uri,
        "response_type": "code",
        "scope": "activity:read_all",
        "approval_prompt": "auto",
    })
    return {"authorize_url": f"https://www.strava.com/oauth/authorize?{params}"}


@router.get("/strava/callback")
def strava_callback(code: str = "") -> dict:
    # TODO step 2: exchange code -> tokens, persist OAuthToken, enqueue initial sync
    return {"status": "todo", "code_received": bool(code)}


@router.get("/spotify/authorize")
def spotify_authorize() -> dict:
    s = get_settings()
    params = urlencode({
        "client_id": s.spotify_client_id,
        "redirect_uri": s.spotify_redirect_uri,
        "response_type": "code",
        "scope": "user-read-recently-played",
    })
    return {"authorize_url": f"https://accounts.spotify.com/authorize?{params}"}


@router.get("/spotify/callback")
def spotify_callback(code: str = "") -> dict:
    # TODO step 4: exchange code -> tokens, persist OAuthToken, enqueue listening sync
    return {"status": "todo", "code_received": bool(code)}
