from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import wellness
from app.database import get_db
from app.models import WellnessSample
from app.schemas import WellnessBatchIn, WellnessIngestOut

router = APIRouter(prefix="/wellness", tags=["wellness"])


@router.post("/ingest", response_model=WellnessIngestOut)
def ingest(payload: WellnessBatchIn, db: Session = Depends(get_db)):
    """Batch ingestion, idempotent on (source, kind, recorded_at) —
    adapters can safely re-send overlapping windows."""
    ingested = duplicates = 0
    for sample in payload.samples:
        exists = db.scalar(select(WellnessSample.id).where(
            WellnessSample.source == sample.source,
            WellnessSample.kind == sample.kind,
            WellnessSample.recorded_at == sample.recorded_at,
        ))
        if exists:
            duplicates += 1
            continue
        db.add(WellnessSample(**sample.model_dump()))
        ingested += 1
    db.commit()
    if ingested:
        wellness.rollup_daily(db)
    return WellnessIngestOut(ingested=ingested, duplicates=duplicates)
