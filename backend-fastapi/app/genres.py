"""LLM-inferred fine-grained genre per listened track, stored on
ListeningSession.genre. Spotify removed its artist-genre endpoint (Feb 2026), so
— like the mood phrase — genre is inferred from track + artist by the LLM."""
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import llm
from app.models import ListeningSession

logger = logging.getLogger(__name__)

BATCH = 50
_LINE = re.compile(r"^\s*(\d+)\s*[.):\-]?\s*(.+?)\s*$")

SYSTEM = """You label music tracks with their specific sub-genre. For each
numbered "track — artist" line, reply with ONE line "N. genre" in the SAME
numbering, where genre is the specific sub-genre in at most 2 words, lowercase
(e.g. trap, cloud rap, phonk, drum and bass, indie rock, synthwave). Output only
those numbered lines, nothing else."""


def infer_pending(db: Session, limit: int = BATCH) -> int:
    """Fill ListeningSession.genre for rows lacking it, via one LLM call.
    Idempotent (touches only genre IS NULL); returns rows updated; 0 offline."""
    rows = list(db.scalars(
        select(ListeningSession)
        .where(ListeningSession.genre.is_(None))
        .order_by(ListeningSession.id)
        .limit(limit)
    ).all())
    if not rows or not llm.is_configured():
        return 0
    listing = "\n".join(f"{i + 1}. {r.track_name} — {r.artist or 'unknown'}"
                        for i, r in enumerate(rows))
    try:
        reply = llm.complete(system=SYSTEM,
                             messages=[{"role": "user", "content": listing}],
                             max_tokens=400)
    except Exception as e:
        logger.warning("genre inference failed: %s", e)
        return 0
    updated = 0
    for line in reply.splitlines():
        m = _LINE.match(line)
        if not m:
            continue
        idx = int(m.group(1)) - 1
        genre = m.group(2).strip().strip('"').lower()[:128]
        if 0 <= idx < len(rows) and genre and rows[idx].genre is None:
            rows[idx].genre = genre
            updated += 1
    db.commit()
    return updated
