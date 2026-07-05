"""Data model.

Effort modes — the physiological backbone of the whole app:
  explosive : sprint / anaerobic power (neural work)
  aerobic   : sustained endurance (engine work)
  loaded    : sustained effort under load — ruck/hike (structural work)
"""
import enum
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Enum, Float, Integer, String, Text, UniqueConstraint
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
