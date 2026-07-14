"""Daily quote — a curated, genuinely-attributed line from thinkers, mountaineers and
endurance athletes, rotating deterministically by day. The personalized daily
*reflection* lives in reflection.py; the training/lens helpers here are shared with it."""
import logging
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Activity, DailyQuote, EffortMode

logger = logging.getLogger(__name__)

# (quote, author) — real, curated attributions. Rotated by day-of-year. Keep quotes
# short and the attributions accurate; do not add lines you can't attribute.
CURATED: list[tuple[str, str]] = [
    ("It is not the mountain we conquer, but ourselves.", "Edmund Hillary"),
    ("Getting to the top is optional. Getting down is mandatory.", "Ed Viesturs"),
    ("The mountains are calling and I must go.", "John Muir"),
    ("We are what we repeatedly do. Excellence, then, is not an act, but a habit.", "Will Durant"),
    ("It does not matter how slowly you go as long as you do not stop.", "Confucius"),
    ("A journey of a thousand miles begins with a single step.", "Lao Tzu"),
    ("You have power over your mind, not outside events. Realize this, and you will find strength.", "Marcus Aurelius"),
    ("We suffer more often in imagination than in reality.", "Seneca"),
    ("No man is free who is not master of himself.", "Epictetus"),
    ("He who has a why to live can bear almost any how.", "Friedrich Nietzsche"),
    ("To give anything less than your best is to sacrifice the gift.", "Steve Prefontaine"),
    ("Pain is inevitable. Suffering is optional.", "Haruki Murakami"),
    ("Only the disciplined ones in life are free.", "Eliud Kipchoge"),
    ("It always seems impossible until it's done.", "Nelson Mandela"),
    ("Adopt the pace of nature: her secret is patience.", "Ralph Waldo Emerson"),
    ("A man can be destroyed but not defeated.", "Ernest Hemingway"),
    ("The impediment to action advances action. What stands in the way becomes the way.", "Marcus Aurelius"),
    ("Do not pray for an easy life; pray for the strength to endure a difficult one.", "Bruce Lee"),
    ("Fall seven times, stand up eight.", "Japanese proverb"),
    ("It is not because things are difficult that we do not dare; it is because we do not dare that they are difficult.", "Seneca"),
    ("The summit is what drives us, but the climb itself is what matters.", "Conrad Anker"),
    ("What we achieve inwardly will change outer reality.", "Plutarch"),
]

# Rotating daily lenses — shared with the reflection so its angle shifts day to day.
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


def get_today(db: Session) -> DailyQuote:
    today = date.today()
    row = db.scalar(select(DailyQuote).where(DailyQuote.day == today))
    if row is not None:
        return row
    text, author = CURATED[today.timetuple().tm_yday % len(CURATED)]
    row = DailyQuote(day=today, text=text, author=author, source="curated")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
