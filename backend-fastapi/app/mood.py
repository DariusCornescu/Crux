"""Current music mood as a short phrase — LLM sentiment of recent listening,
cached per day in daily_moods, deterministic valence-bucket fallback offline."""
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import llm
from app.models import DailyMood, ListeningSession

logger = logging.getLogger(__name__)

RECENT_DAYS = 2

SYSTEM = """You read an athlete's recent music listening and name the emotional
mood in AT MOST 3 words, lowercase (e.g. "low and restless", "locked-in focus",
"bright and loose"). Use the songs, artists, and any valence (0=negative..
1=positive) / energy (0=calm..1=intense) values given. Reply with ONLY the mood
phrase — no quotes, no punctuation at the ends, no explanation."""


def _recent(db: Session) -> list[ListeningSession]:
    since = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)
    return list(db.scalars(
        select(ListeningSession)
        .where(ListeningSession.played_at >= since)
        .order_by(ListeningSession.played_at.desc())
        .limit(40)
    ).all())


def _snapshot(tracks: list[ListeningSession]) -> str:
    lines = []
    for t in tracks:
        extra = ""
        if t.valence is not None:
            extra = f" (valence {t.valence:.2f}, energy {t.energy if t.energy is not None else '?'})"
        lines.append(f"- {t.track_name} — {t.artist or 'unknown'}{extra}")
    return "Recent listening (last 2 days):\n" + "\n".join(lines)


def _fallback(tracks: list[ListeningSession]) -> str:
    if not tracks:
        return "quiet"
    vals = [t.valence for t in tracks if t.valence is not None]
    if not vals:
        return "even"
    avg = sum(vals) / len(vals)
    if avg >= 0.6:
        return "bright"
    if avg >= 0.4:
        return "even"
    return "heavy"


def get_current(db: Session) -> DailyMood:
    today = date.today()
    row = db.scalar(select(DailyMood).where(DailyMood.day == today))
    if row is not None:
        return row
    tracks = _recent(db)
    phrase, source = None, "fallback"
    if tracks and llm.is_configured():
        try:
            phrase = llm.complete(system=SYSTEM,
                                  messages=[{"role": "user", "content": _snapshot(tracks)}],
                                  max_tokens=16).strip().strip('"').strip().lower()[:64]
            source = "llm"
        except Exception as e:
            logger.warning("mood generation failed, using fallback: %s", e)
            phrase = None
    if not phrase:
        phrase, source = _fallback(tracks), "fallback"
    row = DailyMood(day=today, phrase=phrase, source=source)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
