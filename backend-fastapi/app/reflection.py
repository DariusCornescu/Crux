"""Daily reflection — a short LLM meditation tying the week's training to the
current listening mood, cached per day in daily_reflections. Deterministic
templated fallback offline. Same LLM+fallback+per-day-cache shape as quotes.py
and mood.py."""
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import llm, mood, quotes
from app.models import DailyReflection

logger = logging.getLogger(__name__)

# The OpenRouter default is a reasoning model that spends hidden tokens before the
# visible completion, so a 2-3 sentence reflection needs generous headroom.
LLM_MAX_TOKENS = 240

SYSTEM = """You are a terse training philosopher. Given an athlete's week of
training numbers and their current listening mood, write a 2-3 sentence reflection
that ties body and mind together and leaves one grounded thought to carry into the
next session. Dry, timing-sheet tone — not cheerleading. No emoji, no hashtags, no
lists, no surrounding quotes."""

FALLBACK = ("Base laid, mind settled. The work already logged is the work that "
            "counts — let it compound, and meet the next session on its own terms.")


def _prompt(db: Session) -> str:
    snapshot = quotes._week_snapshot(db)
    phrase = mood.get_current(db).phrase
    return f"{snapshot}\nCurrent listening mood: {phrase}."


def get_today(db: Session) -> DailyReflection:
    today = date.today()
    row = db.scalar(select(DailyReflection).where(DailyReflection.day == today))
    if row is not None:
        return row
    text, source = None, "static"
    if llm.is_configured():
        try:
            text = llm.complete(system=SYSTEM,
                                messages=[{"role": "user", "content": _prompt(db)}],
                                max_tokens=LLM_MAX_TOKENS).strip().strip('"')
            source = "llm"
        except Exception as e:
            logger.warning("reflection generation failed, using fallback: %s", e)
            text = None
    if not text:
        text, source = FALLBACK, "static"
    row = DailyReflection(day=today, text=text, source=source)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
