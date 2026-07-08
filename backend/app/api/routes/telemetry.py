from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.telemetry import TelemetryLatest, TelemetryRecord
from app.schemas.common import TelemetryIngestPayload
from app.services.telemetry_ingestion import ingest_payload
from app.services.timezone import iso_beijing

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/latest")
def latest_telemetry(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {
            "id": item.id,
            "deviceId": item.device_id,
            "sensorCode": item.sensor_code,
            "sensorName": item.sensor_name,
            "value": item.value,
            "unit": item.unit,
            "quality": item.quality,
            "commandCode": item.command_code,
            "recordedAt": item.recorded_at.isoformat(),
            "recordedAtBeijing": iso_beijing(item.recorded_at),
        }
        for item in db.query(TelemetryLatest).order_by(TelemetryLatest.device_id.asc()).all()
    ]


@router.get("/history")
def telemetry_history(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {
            "id": item.id,
            "deviceId": item.device_id,
            "sensorCode": item.sensor_code,
            "sensorName": item.sensor_name,
            "value": item.value,
            "unit": item.unit,
            "quality": item.quality,
            "commandCode": item.command_code,
            "recordedAt": item.recorded_at.isoformat(),
            "recordedAtBeijing": iso_beijing(item.recorded_at),
        }
        for item in db.query(TelemetryRecord).order_by(TelemetryRecord.recorded_at.desc()).limit(100).all()
    ]


@router.post("/ingest")
def ingest_telemetry(payload: TelemetryIngestPayload, db: Session = Depends(get_db)) -> dict:
    return ingest_payload(db, payload.model_dump(mode="json"))
