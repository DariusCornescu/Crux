"""Spotify integration (build-order step 4) — listening history as a mood proxy.

NOTE on audio features: Spotify restricted the /v1/audio-features endpoint for
applications created after Nov 2024. We request features and degrade gracefully
(403 -> valence/energy stay NULL) so the sync itself keeps working; mood then
simply reads as "no data" instead of breaking the pipeline.
"""
import logging
from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import DailySummary, ListeningSession, OAuthToken

logger = logging.getLogger(__name__)

TOKEN_URL = "https://accounts.spotify.com/api/token"
RECENT_URL = "https://api.spotify.com/v1/me/player/recently-played"
FEATURES_URL = "https://api.spotify.com/v1/audio-features"
PROVIDER = "spotify"


def _aware(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _store_token(db: Session, payload: dict) -> OAuthToken:
    token = db.scalar(select(OAuthToken).where(OAuthToken.provider == PROVIDER))
    if token is None:
        token = OAuthToken(provider=PROVIDER, access_token="")
        db.add(token)
    token.access_token = payload["access_token"]
    # Spotify does not always return a new refresh token — keep the old one.
    token.refresh_token = payload.get("refresh_token") or token.refresh_token
    if payload.get("expires_in"):
        token.expires_at = datetime.now(timezone.utc) + timedelta(seconds=payload["expires_in"])
    token.scope = payload.get("scope") or token.scope
    db.commit()
    db.refresh(token)
    return token


def exchange_code(db: Session, code: str) -> OAuthToken:
    s = get_settings()
    resp = httpx.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": s.spotify_redirect_uri,
    }, auth=(s.spotify_client_id, s.spotify_client_secret), timeout=20)
    resp.raise_for_status()
    return _store_token(db, resp.json())


def _refresh(db: Session, token: OAuthToken) -> OAuthToken:
    s = get_settings()
    resp = httpx.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": token.refresh_token,
    }, auth=(s.spotify_client_id, s.spotify_client_secret), timeout=20)
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


def _fetch_audio_features(track_ids: list[str], access_token: str) -> dict[str, dict]:
    """Best effort — returns {} when the endpoint is unavailable for this app."""
    if not track_ids:
        return {}
    try:
        resp = httpx.get(FEATURES_URL, params={"ids": ",".join(track_ids)}, timeout=20,
                         headers={"Authorization": f"Bearer {access_token}"})
        if resp.status_code != 200:
            logger.warning("audio-features unavailable (HTTP %d) — storing tracks without mood "
                           "features (endpoint is restricted for post-2024 Spotify apps)",
                           resp.status_code)
            return {}
        return {f["id"]: f for f in resp.json().get("audio_features", []) if f}
    except httpx.HTTPError as e:
        logger.warning("audio-features fetch failed: %s", e)
        return {}


def sync_recently_played(db: Session, limit: int = 50) -> int:
    """Pull recently played tracks, attach audio features when available,
    then refresh the daily mood aggregates. Idempotent on played_at."""
    token = get_valid_token(db)
    if token is None:
        raise RuntimeError("Spotify is not connected")

    resp = httpx.get(RECENT_URL, params={"limit": limit}, timeout=30,
                     headers={"Authorization": f"Bearer {token.access_token}"})
    resp.raise_for_status()

    new_rows: list[tuple[ListeningSession, str]] = []
    for item in resp.json().get("items", []):
        played_at = datetime.fromisoformat(item["played_at"].replace("Z", "+00:00"))
        exists = db.scalar(select(ListeningSession.id).where(ListeningSession.played_at == played_at))
        if exists:
            continue
        track = item.get("track") or {}
        row = ListeningSession(
            played_at=played_at,
            track_name=track.get("name") or "unknown",
            artist=", ".join(a.get("name", "") for a in track.get("artists", [])) or None,
        )
        db.add(row)
        new_rows.append((row, track.get("id") or ""))

    features = _fetch_audio_features([tid for _, tid in new_rows if tid], token.access_token)
    for row, tid in new_rows:
        f = features.get(tid)
        if f:
            row.valence = f.get("valence")
            row.energy = f.get("energy")
            row.tempo = f.get("tempo")

    token.last_synced_at = datetime.now(timezone.utc)
    db.commit()

    aggregate_daily_mood(db)
    logger.info("Spotify sync: %d new listening sessions", len(new_rows))
    return len(new_rows)


def aggregate_daily_mood(db: Session, days: int = 14) -> None:
    """Roll per-track valence/energy up into DailySummary mood columns."""
    since = date.today() - timedelta(days=days)
    rows = db.execute(
        select(
            func.date(ListeningSession.played_at),
            func.avg(ListeningSession.valence),
            func.avg(ListeningSession.energy),
        )
        .where(ListeningSession.played_at >= datetime.combine(since, datetime.min.time()))
        .group_by(func.date(ListeningSession.played_at))
    ).all()

    for day_value, avg_valence, avg_energy in rows:
        day = day_value if isinstance(day_value, date) else date.fromisoformat(str(day_value))
        summary = db.scalar(select(DailySummary).where(DailySummary.day == day))
        if summary is None:
            summary = DailySummary(day=day)
            db.add(summary)
        summary.mood_valence = float(avg_valence) if avg_valence is not None else None
        summary.mood_energy = float(avg_energy) if avg_energy is not None else None
    db.commit()
