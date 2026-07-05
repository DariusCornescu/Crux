from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import ActivityType, EffortMode


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    name: str | None = None
    type: ActivityType
    mode: EffortMode
    start_time: datetime
    duration_s: int
    distance_m: float | None = None
    avg_pace_s_per_km: float | None = None
    elevation_gain_m: float | None = None
    avg_hr: int | None = None
    load_kg: float | None = None
    splits: list | None = None
    perceived_effort: int | None = None


class ActivityCreate(BaseModel):
    type: ActivityType
    name: str | None = None
    start_time: datetime
    duration_s: int
    distance_m: float | None = None
    avg_pace_s_per_km: float | None = None
    elevation_gain_m: float | None = None
    avg_hr: int | None = None
    load_kg: float | None = None
    splits: list[float] | None = None
    perceived_effort: int | None = None


class PacingEstimateIn(BaseModel):
    distance_m: float
    elevation_gain_m: float


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    period_start: date
    period_end: date
    body_md: str
    highlights: dict | None = None
    created_at: datetime


class VoiceLogCreate(BaseModel):
    transcript: str
    lang: str | None = None
    activity_id: int | None = None
    created_at: datetime | None = None


class VoiceLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    activity_id: int | None = None
    lang: str | None = None
    transcript: str
    perceived_effort: int | None = None
    session_type: ActivityType | None = None
    notes: str | None = None
    extraction_method: str
    extracted: dict | None = None


class ReportGenerateIn(BaseModel):
    week_start: date | None = None


class ChatIn(BaseModel):
    message: str


class ChatOut(BaseModel):
    reply: str


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class DeviceRegisterIn(BaseModel):
    token: str
    platform: str = "android"


# ---- Wellness (wearable ingestion) ----

class WellnessSampleIn(BaseModel):
    recorded_at: datetime
    kind: str
    value: float
    source: str = "health_connect"

    @field_validator("kind")
    @classmethod
    def _known_kind(cls, v: str) -> str:
        from app.wellness import ALLOWED_KINDS

        if v not in ALLOWED_KINDS:
            raise ValueError(f"unknown kind {v!r} (allowed: {sorted(ALLOWED_KINDS)})")
        return v


class WellnessBatchIn(BaseModel):
    samples: list[WellnessSampleIn]


class WellnessIngestOut(BaseModel):
    ingested: int
    duplicates: int


# ---- Integrations ----

class IntegrationState(BaseModel):
    connected: bool = False
    athlete_id: str | None = None
    last_synced_at: datetime | None = None


class IntegrationsStatus(BaseModel):
    strava: IntegrationState
    spotify: IntegrationState
    calendar: IntegrationState = IntegrationState()


class SyncResult(BaseModel):
    synced: int


# ---- Dashboard payload: one block per instrument ----

class Conditions(BaseModel):
    sleep_min: int | None = None
    resting_hr: int | None = None
    mood_valence: float | None = None


class MoodPoint(BaseModel):
    day: date
    valence: float | None = None


class RailEntry(BaseModel):
    day: date
    mode: EffortMode
    type: ActivityType
    duration_s: int
    best_split: float | None = None  # explosive
    distance_m: float | None = None  # aerobic
    vert_m: float | None = None      # loaded


class GateBlock(BaseModel):
    best_split: float | None = None
    pb: float = 6.91
    session_note: str | None = None
    splits: list[float] = []


class StripBlock(BaseModel):
    week_km: float = 0
    long_run_km: float = 0
    z2_pct: float | None = None
    pace_trend: list[float] = []  # s/km, most recent run per-km


class AltiBlock(BaseModel):
    vert_m: float = 0
    goal_m: float = 2000
    load_kg: float | None = None
    carries: int = 0


class DashboardOut(BaseModel):
    week: int
    demo: bool = False
    conditions: Conditions
    mood_trend: list[MoodPoint] = []
    rail: list[RailEntry]
    gate: GateBlock
    strip: StripBlock
    alti: AltiBlock
