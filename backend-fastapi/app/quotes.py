"""Daily motivational line — LLM-personalized from the week's training, the current
music mood, and a rotating daily philosophical lens, cached per day in daily_quotes.
The lens + mood keep the line varying day to day even when training is flat.
Deterministic static fallback offline."""
import logging
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import llm
from app.models import Activity, DailyMood, DailyQuote, EffortMode

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

# Rotating daily lenses — the angle the day's line is written through, so the
# philosophy shifts day to day even during a quiet training block.
LENSES = [
    "discipline over motivation",
    "patience and the long base",
    "the mountain's indifference",
    "rest as part of the work",
    "hunger for the climb",
    "the body as an honest ledger",
    "consistency compounding quietly",
    "stillness before effort",
    "breath and rhythm",
    "the gap between knowing and doing",
    "small repeatable habits",
    "the sprinter learning to wait",
    "weather and things you cannot control",
    "showing up on the dull days",
]

SYSTEM = """Write ONE short line (max 120 characters) of dry, grounded training
philosophy for an athlete — a former 60m sprint champion rebuilding aerobic base and
preparing for the mountains. You are given the week's training numbers, days since
the last session, the current music mood, and TODAY'S LENS. Write THROUGH the lens
and let the mood colour it, so each day reads differently. If training is quiet, treat
rest and patience as part of the work — never shame inactivity, and never reuse
yesterday's framing. No surrounding quotes, no emoji, no hashtags. Not cheerleading."""


def lens_for(day: date) -> str:
    """Deterministic rotating lens — cycles through LENSES by day of year."""
    return LENSES[day.timetuple().tm_yday % len(LENSES)]


def _week_snapshot(db: Session) -> str:
    today = date.today()
    week_start = datetime.combine(today - timedelta(days=today.weekday()),
                                  time.min, tzinfo=timezone.utc)
    activities = db.scalars(select(Activity).where(Activity.start_time >= week_start)).all()
    km = sum((a.distance_m or 0) / 1000 for a in activities if a.mode == EffortMode.aerobic)
    vert = sum(a.elevation_gain_m or 0 for a in activities if a.mode == EffortMode.loaded)
    return (f"This week so far: {len(activities)} sessions, {km:.1f} km aerobic, "
            f"{int(vert)} m vertical under load.")


def _days_since_last_session(db: Session) -> str:
    last = db.scalar(select(func.max(Activity.start_time)))
    if last is None:
        return "No training sessions logged yet."
    days = (datetime.now(timezone.utc) - last).days
    return f"Last logged session was {days} days ago."


def _todays_mood(db: Session) -> str | None:
    row = db.scalar(select(DailyMood).where(DailyMood.day == date.today()))
    return row.phrase if row else None


def _context(db: Session) -> str:
    parts = [_week_snapshot(db), _days_since_last_session(db)]
    mood = _todays_mood(db)
    if mood:
        parts.append(f"Current music mood: {mood}.")
    parts.append(f"Today's lens: {lens_for(date.today())}.")
    return "\n".join(parts)


def get_today(db: Session) -> DailyQuote:
    today = date.today()
    row = db.scalar(select(DailyQuote).where(DailyQuote.day == today))
    if row is not None:
        return row
    text, source = None, "static"
    if llm.is_configured():
        try:
            text = llm.complete(system=SYSTEM,
                                messages=[{"role": "user", "content": _context(db)}],
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
