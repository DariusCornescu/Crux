"""Daily motivational line — LLM-personalized from the week's training, cached
per day in daily_quotes, deterministic static fallback offline."""
import logging
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import llm
from app.models import Activity, DailyQuote, EffortMode

logger = logging.getLogger(__name__)

STATIC_QUOTES = [
    "The mountain doesn't care how you feel. Show up anyway.",
    "Base miles are deposits. Race day makes the withdrawal.",
    "Slow is smooth, smooth is far.",
    "You don't rise to the summit; you fall to your training.",
    "Heavy pack, light mind.",
    "Consistency beats intensity when intensity quits.",
    "Every easy kilometer is a brick in the engine.",
    "The best pace is the one you can hold tomorrow too.",
    "Vertical meters are honest meters.",
    "Train the engine, respect the springs.",
    "No wind is unfair if you packed for it.",
    "Today's discipline is next season's freedom.",
]

SYSTEM = """Write ONE short motivational line (max 120 characters) for an athlete
rebuilding aerobic base and preparing for mountaineering. Reference the training
numbers given if useful. No quotes around it, no emoji, no hashtags. Dry,
timing-sheet tone — not cheerleading."""


def _week_snapshot(db: Session) -> str:
    today = date.today()
    week_start = datetime.combine(today - timedelta(days=today.weekday()),
                                  time.min, tzinfo=timezone.utc)
    activities = db.scalars(select(Activity).where(Activity.start_time >= week_start)).all()
    km = sum((a.distance_m or 0) / 1000 for a in activities if a.mode == EffortMode.aerobic)
    vert = sum(a.elevation_gain_m or 0 for a in activities if a.mode == EffortMode.loaded)
    return (f"This week so far: {len(activities)} sessions, {km:.1f} km aerobic, "
            f"{int(vert)} m vertical under load.")


def get_today(db: Session) -> DailyQuote:
    today = date.today()
    row = db.scalar(select(DailyQuote).where(DailyQuote.day == today))
    if row is not None:
        return row
    text, source = None, "static"
    if llm.is_configured():
        try:
            text = llm.complete(system=SYSTEM,
                                messages=[{"role": "user", "content": _week_snapshot(db)}],
                                max_tokens=160).strip().strip('"')
            source = "llm"
        except Exception as e:
            logger.warning("quote generation failed, using static: %s", e)
            text = None
    if not text:
        text, source = STATIC_QUOTES[today.timetuple().tm_yday % len(STATIC_QUOTES)], "static"
    row = DailyQuote(day=today, text=text, source=source)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
