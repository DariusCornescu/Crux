"""OAuth + sync endpoints for Strava (step 2) and Spotify (step 4).

Thin routing layer — the actual work lives in app/strava.py and
app/spotify.py, mirroring ListManagerApp's flat service modules.
"""
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import calendar_sync, spotify, strava
from app.config import get_settings
from app.database import get_db
from app.models import OAuthToken
from app.schemas import IntegrationState, IntegrationsStatus, SyncResult

router = APIRouter(prefix="/integrations", tags=["integrations"])

# Minimal "return to the app" page, in meet-sheet colors.
_CALLBACK_HTML = """<!doctype html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
 body {{ background:#EFEAE0; color:#16181D; font-family:monospace;
        display:flex; align-items:center; justify-content:center; height:100vh; }}
 .panel {{ border-top:1px solid rgba(22,24,29,.22); border-bottom:1px solid rgba(22,24,29,.22);
          padding:24px 32px; text-align:center; letter-spacing:2px; }}
 .ok {{ color:#C33B2A; }}
</style></head>
<body><div class="panel"><div class="ok">{title}</div><div>{note}</div></div></body></html>"""


def _state(db: Session, provider: str) -> IntegrationState:
    token = db.scalar(select(OAuthToken).where(OAuthToken.provider == provider))
    if token is None:
        return IntegrationState()
    return IntegrationState(connected=True, athlete_id=token.athlete_id,
                            last_synced_at=token.last_synced_at)


def _calendar_state(db: Session) -> IntegrationState:
    state = _state(db, calendar_sync.PROVIDER)
    return IntegrationState(connected=bool(get_settings().calendar_ics_url),
                            last_synced_at=state.last_synced_at)


@router.get("/status", response_model=IntegrationsStatus)
def status(db: Session = Depends(get_db)):
    return IntegrationsStatus(strava=_state(db, "strava"), spotify=_state(db, "spotify"),
                              calendar=_calendar_state(db))


# ---- Strava ----

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


@router.get("/strava/callback", response_class=HTMLResponse)
def strava_callback(code: str = "", error: str = "", db: Session = Depends(get_db)):
    if error or not code:
        return _CALLBACK_HTML.format(title="STRAVA — NOT CONNECTED", note=error or "no code")
    strava.exchange_code(db, code)
    try:
        strava.sync_activities(db)
    except Exception:  # initial sync is best effort; the beat schedule retries
        pass
    return _CALLBACK_HTML.format(title="STRAVA CONNECTED", note="return to Splitrail")


@router.post("/strava/sync", response_model=SyncResult)
def strava_sync(db: Session = Depends(get_db)):
    try:
        return SyncResult(synced=strava.sync_activities(db))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- Spotify ----

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


@router.get("/spotify/callback", response_class=HTMLResponse)
def spotify_callback(code: str = "", error: str = "", db: Session = Depends(get_db)):
    if error or not code:
        return _CALLBACK_HTML.format(title="SPOTIFY — NOT CONNECTED", note=error or "no code")
    spotify.exchange_code(db, code)
    try:
        spotify.sync_recently_played(db)
    except Exception:
        pass
    return _CALLBACK_HTML.format(title="SPOTIFY CONNECTED", note="return to Splitrail")


@router.post("/spotify/sync", response_model=SyncResult)
def spotify_sync(db: Session = Depends(get_db)):
    try:
        return SyncResult(synced=spotify.sync_recently_played(db))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- Work calendar (published ICS feed — see calendar_sync.py) ----

@router.post("/calendar/sync", response_model=SyncResult)
def calendar_sync_now(db: Session = Depends(get_db)):
    try:
        return SyncResult(synced=calendar_sync.sync_ics(db))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
