"""Detail payload behind the Dashboard's tappable COND/MoodTrace region."""
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import mood
from app.database import get_db
from app.models import DailySummary, ListeningSession
from app.schemas import GenreCount, SignalDay, SignalsOut, SignalTrack

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/detail", response_model=SignalsOut)
def detail(db: Session = Depends(get_db)):
    tracks = db.scalars(select(ListeningSession)
                        .order_by(ListeningSession.played_at.desc()).limit(30)).all()
    days = db.scalars(select(DailySummary)
                      .order_by(DailySummary.day.desc()).limit(14)).all()
    genre_counts = Counter(t.genre for t in tracks if t.genre)
    return SignalsOut(
        recent_tracks=[SignalTrack(played_at=t.played_at, track=t.track_name, artist=t.artist,
                                   valence=t.valence, energy=t.energy) for t in tracks],
        daily=[SignalDay(day=d.day, sleep_min=d.sleep_duration_min, sleep_score=d.sleep_score,
                         resting_hr=d.resting_hr, steps=d.steps, mood_valence=d.mood_valence,
                         mood_energy=d.mood_energy) for d in days],
        current_mood=mood.get_current(db).phrase,
        genres=[GenreCount(genre=g, count=c) for g, c in genre_counts.most_common()],
    )
