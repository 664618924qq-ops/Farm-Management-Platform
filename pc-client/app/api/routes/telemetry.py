from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.telemetry import TelemetryRecord


router = APIRouter()


@router.get("/latest")
def latest_telemetry(db: Session = Depends(get_db)) -> list[dict]:
    rows = (
        db.query(TelemetryRecord)
        .order_by(TelemetryRecord.collected_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": row.id,
            "device_id": row.device_id,
            "metric_code": row.metric_code,
            "metric_name": row.metric_name,
            "metric_value": row.metric_value,
            "metric_unit": row.metric_unit,
            "quality": row.quality,
            "collected_at": row.collected_at,
        }
        for row in rows
    ]
