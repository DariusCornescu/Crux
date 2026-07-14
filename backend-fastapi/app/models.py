"""Data model.

Effort modes — the physiological backbone of the whole app:
  explosive : sprint / anaerobic power (neural work)
  aerobic   : sustained endurance (engine work)
  loaded    : sustained effort under load — ruck/hike (structural work)
"""
import enum
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ActivityType(str, enum.Enum):
    sprint = "sprint"
    tempo = "tempo"
    easy_run = "easy_run"
    hike = "hike"
    ruck = "ruck"
    strength = "strength"


class EffortMode(str, enum.Enum):
    explosive = "explosive"
    aerobic = "aerobic"
    loaded = "loaded"


TYPE_TO_MODE: dict[ActivityType, EffortMode] = {
    ActivityType.sprint: EffortMode.explosive,
    ActivityType.strength: EffortMode.explosive,  # crude for now; revisit per-session
    ActivityType.tempo: EffortMode.aerobic,
    ActivityType.easy_run: EffortMode.aerobic,
    ActivityType.hike: EffortMode.loaded,
    ActivityType.ruck: EffortMode.loaded,
}


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_activity_source_ext"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(32))  # strava | manual | health_connect
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)  # e.g. Strava title
    type: Mapped[ActivityType] = mapped_column(Enum(ActivityType))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_s: Mapped[int] = mapped_column(Integer)
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_pace_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hr_zones: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"z1": s, ..., "z5": s}
    load_kg: Mapped[float | None] = mapped_column(Float, nullable=True)  # ruck weight
    splits: Mapped[list | None] = mapped_column(JSON, nullable=True)  # sprint reps: [7.04, 6.98, ...]
    perceived_effort: Mapped[int | None] = mapped_column(Integer, nullable=True)  # RPE 1-10
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # source payload

    @property
    def mode(self) -> EffortMode:
        return TYPE_TO_MODE[self.type]


class ListeningSession(Base):
    __tablename__ = "listening_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, unique=True)
    track_name: Mapped[str] = mapped_column(String(256))
    artist: Mapped[str | None] = mapped_column(String(256), nullable=True)
    spotify_track_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    valence: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0..1
    energy: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0..1
    tempo: Mapped[float | None] = mapped_column(Float, nullable=True)  # BPM
    genre: Mapped[str | None] = mapped_column(String(128), nullable=True)


class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True, index=True)
    training_load: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    resting_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mood_valence: Mapped[float | None] = mapped_column(Float, nullable=True)  # listening-derived
    mood_energy: Mapped[float | None] = mapped_column(Float, nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # weekly | monthly
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    body_md: Mapped[str] = mapped_column(Text)
    highlights: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), unique=True)  # strava | spotify
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[str | None] = mapped_column(String(256), nullable=True)
    athlete_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(512), unique=True)
    platform: Mapped[str] = mapped_column(String(16), default="android")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class VoiceLog(Base):
    __tablename__ = "voice_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id"), nullable=True)
    lang: Mapped[str | None] = mapped_column(String(8), nullable=True)      # "ro" | "en" | "mixed"
    transcript: Mapped[str] = mapped_column(Text)
    # --- extracted structured fields ---
    perceived_effort: Mapped[int | None] = mapped_column(Integer, nullable=True)   # RPE 1-10
    session_type: Mapped[ActivityType | None] = mapped_column(Enum(ActivityType), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)         # subjective summary
    extraction_method: Mapped[str] = mapped_column(String(16), default="none")  # deterministic|llm|none
    extracted: Mapped[dict | None] = mapped_column(JSON, nullable=True)    # full struct: {symptoms:[], terrain:[], ...}


class WellnessSample(Base):
    """Intraday wearable data (build: stress-schedule-wearable Phase A).

    Device-agnostic: Health Connect, vendor cloud adapters, or manual POSTs
    all land here. Intraday timestamps on purpose — the hour-of-day stress
    profile needs time resolution, not daily averages.
    """
    __tablename__ = "wellness_samples"
    __table_args__ = (UniqueConstraint("source", "kind", "recorded_at",
                                       name="uq_wellness_source_kind_time"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    kind: Mapped[str] = mapped_column(String(16))    # see wellness.ALLOWED_KINDS
    value: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(16), default="health_connect")


class CalendarEvent(Base):
    """Work-calendar busy blocks (stress-schedule-wearable spec, Phase B).

    Server is user-owned/single-tenant, so real meeting subjects are stored
    (Dashboard v2 AGENDA block) alongside a salted SHA-256 of the subject,
    kept for dedup/upsert matching independent of the display text.
    """
    __tablename__ = "calendar_events"
    __table_args__ = (UniqueConstraint("source", "subject_hash", "start",
                                       name="uq_calendar_source_subject_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    busy_status: Mapped[str] = mapped_column(String(16), default="busy")
    attendee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    subject_hash: Mapped[str] = mapped_column(String(64))
    subject: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="ics")


class DailyQuote(Base):
    __tablename__ = "daily_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True, index=True)
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(8), default="static")  # curated | llm | static
    author: Mapped[str | None] = mapped_column(String(64), nullable=True)  # attribution, when curated


class DailyMood(Base):
    __tablename__ = "daily_moods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True, index=True)
    phrase: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(8), default="fallback")  # llm | fallback


class DailyReflection(Base):
    """The daily philosophical reflection — a short LLM meditation tying the
    week's training to the current listening mood, cached one row per day."""
    __tablename__ = "daily_reflections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True, index=True)
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(8), default="static")  # llm | static


class DailyContribution(Base):
    """GitHub contribution count per day — coding treated as another discipline.
    One row per day; source records whether counts came from the GraphQL calendar
    or the approximate public-events feed."""
    __tablename__ = "daily_contributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(16), default="events")  # graphql | events
