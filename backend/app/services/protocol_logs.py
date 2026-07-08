from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.protocol import ProtocolUploadLog
from app.services.hj212 import HJ212Message
from app.services.timezone import beijing_now_naive, iso_beijing


def create_protocol_log(
    db: Session,
    *,
    source: str,
    raw_packet: str,
    status: str,
    message: HJ212Message | None = None,
    metric_count: int = 0,
    ack_packet: str | None = None,
    error_message: str | None = None,
) -> ProtocolUploadLog:
    log = ProtocolUploadLog(
        source=source,
        mn=message.mn if message else None,
        cn=message.cn if message else None,
        qn=message.qn if message else None,
        data_time=message.data_time if message else None,
        status=status,
        metric_count=metric_count,
        raw_packet=raw_packet,
        ack_packet=ack_packet,
        error_message=error_message,
        received_at=beijing_now_naive(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def serialize_protocol_log(log: ProtocolUploadLog) -> dict:
    data_time_beijing = iso_beijing(log.data_time)
    received_at_beijing = iso_beijing(log.received_at)
    return {
        "id": log.id,
        "source": log.source,
        "mn": log.mn,
        "cn": log.cn,
        "qn": log.qn,
        "dataTime": log.data_time.isoformat() if log.data_time else None,
        "dataTimeBeijing": data_time_beijing,
        "status": log.status,
        "metricCount": log.metric_count,
        "rawPacket": log.raw_packet,
        "ackPacket": log.ack_packet,
        "errorMessage": log.error_message,
        "receivedAt": received_at_beijing,
        "receivedAtBeijing": received_at_beijing,
        "storedAtBeijing": received_at_beijing,
    }
