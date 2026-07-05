"""Strava integration (build-order step 2).

Flat service module, ListManagerApp-style (cf. its transcription.py):
token exchange/refresh and the activity sync live here; routers stay thin.
"""
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Activity, ActivityType, OAuthToken

logger = logging.getLogger(__name__)

TOKEN_URL = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
PROVIDER = "strava"


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _store_token(db: Session, payload: dict) -> OAuthToken:
    token = db.scalar(select(OAuthToken).where(OAuthToken.provider == PROVIDER))
    if token is None:
        token = OAuthToken(provider=PROVIDER, access_token="")
        db.add(token)
    token.access_token = payload["access_token"]
    token.refresh_token = payload.get("refresh_token") or token.refresh_token
    if payload.get("expires_at"):
        token.expires_at = datetime.fromtimestamp(payload["expires_at"], tz=timezone.utc)
    athlete = payload.get("athlete") or {}
    if athlete.get("id"):
        token.athlete_id = str(athlete["id"])
    db.commit()
    db.refresh(token)
    return token


def exchange_code(db: Session, code: str) -> OAuthToken:
    s = get_settings()
    resp = httpx.post(TOKEN_URL, data={
        "client_id": s.strava_client_id,
        "client_secret": s.strava_client_secret,
        "code": code,
        "grant_type": "authorization_code",
    }, timeout=20)
    resp.raise_for_status()
    return _store_token(db, resp.json())


def _refresh(db: Session, token: OAuthToken) -> OAuthToken:
    s = get_settings()
    resp = httpx.post(TOKEN_URL, data={
        "client_id": s.strava_client_id,
        "client_secret": s.strava_client_secret,
        "grant_type": "refresh_token",
        "refresh_token": token.refresh_token,
    }, timeout=20)
    resp.raise_for_status()
    return _store_token(db, resp.json())


def get_valid_token(db: Session) -> OAuthToken | None:
    token = db.scalar(select(OAuthToken).where(OAuthToken.provider == PROVIDER))
    if token is None:
        return None
    expires_at = _aware(token.expires_at)
    if expires_at and expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5):
        token = _refresh(db, token)
    return token


def classify(sport_type: str, name: str | None) -> ActivityType:
    """Map a Strava activity to an effort type.

    Heuristic, deliberately transparent: the title wins ("ruck", "tempo",
    "sprint" in the name), then the sport type. Hand-timed sprint sessions
    come in via POST /activities anyway — Strava won't carry 60m splits.
    """
    n = (name or "").lower()
    if "ruck" in n:
        return ActivityType.ruck
    if "sprint" in n or "speed" in n:
        return ActivityType.sprint
    if "tempo" in n or "threshold" in n:
        return ActivityType.tempo
    if sport_type in ("Hike", "Walk", "Snowshoe"):
        return ActivityType.hike
    if sport_type in ("Run", "TrailRun", "VirtualRun"):
        return ActivityType.easy_run
    if sport_type in ("WeightTraining", "Workout", "Crossfit"):
        return ActivityType.strength
    return ActivityType.easy_run


def sync_activities(db: Session, per_page: int = 50) -> int:
    """Pull recent activities and upsert them. Returns number touched.

    Idempotent via the (source, external_id) unique constraint. A 1-day
    overlap window guards against activities uploaded late.
    """
    token = get_valid_token(db)
    if token is None:
        raise RuntimeError("Strava is not connected")

    params: dict = {"per_page": per_page}
    last = _aware(token.last_synced_at)
    if last:
        params["after"] = int((last - timedelta(days=1)).timestamp())

    resp = httpx.get(ACTIVITIES_URL, params=params, timeout=30,
                     headers={"Authorization": f"Bearer {token.access_token}"})
    resp.raise_for_status()

    count = 0
    for item in resp.json():
        ext_id = str(item["id"])
        activity = db.scalar(select(Activity).where(
            Activity.source == PROVIDER, Activity.external_id == ext_id))
        if activity is None:
            activity = Activity(source=PROVIDER, external_id=ext_id,
                                type=ActivityType.easy_run,
                                start_time=datetime.now(timezone.utc), duration_s=0)
            db.add(activity)

        distance_m = float(item.get("distance") or 0)
        moving_s = int(item.get("moving_time") or 0)
        activity.name = item.get("name")
        activity.type = classify(item.get("sport_type") or item.get("type") or "", item.get("name"))
        activity.start_time = datetime.fromisoformat(item["start_date"].replace("Z", "+00:00"))
        activity.duration_s = moving_s
        activity.distance_m = distance_m or None
        activity.avg_pace_s_per_km = (moving_s / (distance_m / 1000)) if distance_m > 0 else None
        activity.elevation_gain_m = item.get("total_elevation_gain")
        activity.avg_hr = int(item["average_heartrate"]) if item.get("average_heartrate") else None
        activity.raw = {k: item.get(k) for k in ("id", "sport_type", "type", "name")}
        count += 1

    token.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Strava sync: %d activities upserted", count)
    return count
