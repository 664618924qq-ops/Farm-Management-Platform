from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.alert import AlertRecord
from app.models.device import Device
from app.models.farm import Farm
from app.models.protocol import ProtocolUploadLog
from app.models.shed import Shed
from app.models.telemetry import TelemetryRecord
from app.services.timezone import iso_beijing

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)) -> dict:
    latest_protocol = (
        db.query(ProtocolUploadLog)
        .order_by(ProtocolUploadLog.received_at.desc(), ProtocolUploadLog.id.desc())
        .first()
    )
    receive_result = None
    ack_status = None
    ack_summary = None
    if latest_protocol is not None:
        if latest_protocol.status == "accepted":
            receive_result = f"{latest_protocol.source.upper()} accepted and stored"
        elif latest_protocol.status == "rejected":
            receive_result = f"{latest_protocol.source.upper()} received but parse rejected"
        elif latest_protocol.status == "ingest_failed":
            receive_result = f"{latest_protocol.source.upper()} parsed but ingest failed"
        else:
            receive_result = latest_protocol.status
        if latest_protocol.ack_packet and "CN=9014" in latest_protocol.ack_packet:
            ack_status = "valid_9014_ack"
            ack_summary = "CN=9014 ACK returned"
        elif latest_protocol.status == "accepted":
            ack_status = "missing_ack"
            ack_summary = "Accepted but ACK not recorded"
        else:
            ack_status = "not_applicable"
            ack_summary = "No success ACK for this packet"

    return {
        "farmCount": db.query(Farm).count(),
        "shedCount": db.query(Shed).count(),
        "onlineDeviceCount": db.query(Device).filter(Device.status == "online").count(),
        "activeAlertCount": db.query(AlertRecord).filter(AlertRecord.status == "active").count(),
        "integrationStatus": {
            "lastPacketTime": iso_beijing(latest_protocol.received_at) if latest_protocol else None,
            "lastDevice": latest_protocol.mn if latest_protocol else None,
            "lastStatus": latest_protocol.status if latest_protocol else None,
            "lastReceiveResult": receive_result,
            "lastCommand": latest_protocol.cn if latest_protocol else None,
            "lastMetricCount": latest_protocol.metric_count if latest_protocol else 0,
            "lastAckStatus": ack_status,
            "lastAckSummary": ack_summary,
        },
    }


@router.get("/trends")
def get_trends(db: Session = Depends(get_db)) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    records = db.query(TelemetryRecord).order_by(TelemetryRecord.recorded_at.asc()).all()
    for record in records[-40:]:
        grouped[record.sensor_code].append(
            {
                "time": record.recorded_at.isoformat(),
                "value": record.value,
                "unit": record.unit,
            }
        )
    return [{"sensorCode": sensor_code, "points": points} for sensor_code, points in grouped.items()]
