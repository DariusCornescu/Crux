"""Spotify integration (build-order step 4) — listening history as a mood proxy.

NOTE on audio features: Spotify restricted its own /v1/audio-features endpoint for
applications created after Nov 2024, so we fetch features from ReccoBeats instead
(a free, no-auth API that accepts Spotify track ids). We still degrade gracefully
when ReccoBeats can't serve a track/batch (valence/energy stay NULL) so the sync
itself keeps working; mood then simply reads as "no data" instead of breaking the
pipeline.
"""
import logging
import time
from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import genres
from app.config import get_settings
from app.models import DailySummary, ListeningSession, OAuthToken

logger = logging.getLogger(__name__)

TOKEN_URL = "https://accounts.spotify.com/api/token"
RECENT_URL = "https://api.spotify.com/v1/me/player/recently-played"
PROVIDER = "spotify"
RECCO_BATCH = 40
RECCO_DELAY_S = 0.5


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


def _fetch_audio_features(track_ids: list[str]) -> dict[str, dict]:
    """Best effort via ReccoBeats — Spotify's own audio-features endpoint is gone
    for apps created after Nov 2024. Returns {spotify_track_id: feature dict};
    skips any track/batch the service can't serve (valence stays NULL)."""
    if not track_ids:
        return {}
    base = get_settings().reccobeats_base_url
    out: dict[str, dict] = {}
    for i in range(0, len(track_ids), RECCO_BATCH):
        if i:
            time.sleep(RECCO_DELAY_S)  # ReccoBeats rate limit
        batch = track_ids[i:i + RECCO_BATCH]
        try:
            resp = httpx.get(f"{base}/v1/audio-features",
                             params={"ids": ",".join(batch)}, timeout=20)
            if resp.status_code != 200:
                logger.warning("ReccoBeats audio-features unavailable (HTTP %d)", resp.status_code)
                continue
            items = resp.json().get("content") or []
        except (httpx.HTTPError, ValueError, AttributeError) as e:
            logger.warning("ReccoBeats fetch failed: %s", e)
            continue
        parsed = 0
        for f in items:
            if not isinstance(f, dict):
                continue
            href = f.get("href") or ""
            sid = href.rstrip("/").rsplit("/", 1)[-1].split("?")[0] if href else None
            if sid:
                out[sid] = f
                parsed += 1
        if items and not parsed:
            logger.warning("ReccoBeats returned %d items but no parseable spotify ids "
                           "(unexpected href shape?)", len(items))
    return out


def sync_recently_played(db: Session, limit: int = 50) -> int:
    """Pull recently played tracks, attach audio features when available,
    then refresh the daily mood aggregates. Idempotent on played_at."""
    token = get_valid_token(db)
    if token is None:
        raise RuntimeError("Spotify is not connected")

    resp = httpx.get(RECENT_URL, params={"limit": limit}, timeout=30,
                     headers={"Authorization": f"Bearer {token.access_token}"})
    resp.raise_for_status()

    new_rows: list[ListeningSession] = []
    for item in resp.json().get("items", []):
        played_at = datetime.fromisoformat(item["played_at"].replace("Z", "+00:00"))
        track = item.get("track") or {}
        existing = db.scalar(select(ListeningSession).where(ListeningSession.played_at == played_at))
        if existing is not None:
            # Rows stored before spotify_track_id existed: adopt the id so the
            # backfill endpoint can fetch their audio features.
            if existing.spotify_track_id is None and track.get("id"):
                existing.spotify_track_id = track.get("id")
            continue
        row = ListeningSession(
            played_at=played_at,
            track_name=track.get("name") or "unknown",
            artist=", ".join(a.get("name", "") for a in track.get("artists", [])) or None,
            spotify_track_id=track.get("id"),
        )
        db.add(row)
        new_rows.append(row)

    features = _fetch_audio_features(list(dict.fromkeys(
        r.spotify_track_id for r in new_rows if r.spotify_track_id)))
    for r in new_rows:
        f = features.get(r.spotify_track_id)
        if f:
            r.valence = f.get("valence")
            r.energy = f.get("energy")
            r.tempo = f.get("tempo")

    token.last_synced_at = datetime.now(timezone.utc)
    db.commit()

    aggregate_daily_mood(db)
    try:
        genres.infer_pending(db)
    except Exception as e:  # never let genre labelling break a sync
        logger.warning("genre inference skipped: %s", e)
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


def backfill_audio_features(db: Session) -> int:
    """Re-fetch ReccoBeats features for already-synced tracks that have a
    spotify_track_id but no valence. Idempotent; returns rows updated."""
    rows = db.scalars(
        select(ListeningSession).where(
            ListeningSession.spotify_track_id.is_not(None),
            ListeningSession.valence.is_(None),
        )
    ).all()
    if not rows:
        return 0
    features = _fetch_audio_features(list(dict.fromkeys(r.spotify_track_id for r in rows)))
    updated = 0
    for r in rows:
        f = features.get(r.spotify_track_id)
        if f:
            r.valence = f.get("valence")
            r.energy = f.get("energy")
            r.tempo = f.get("tempo")
            updated += 1
    db.commit()
    # Widen the roll-up window to cover the oldest backfilled row — the default
    # 14 days would silently skip older tracks.
    oldest = min(r.played_at for r in rows).date()
    aggregate_daily_mood(db, days=max(14, (date.today() - oldest).days + 1))
    return updated
