from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.protocol import ProtocolUploadLog
from app.services.hj212 import build_data_ack, parse_message
from app.services.protocol_logs import create_protocol_log, serialize_protocol_log
from app.services.telemetry_ingestion import ingest_payload, normalize_hj212_message
from app.services.timezone import parse_beijing_datetime

router = APIRouter(prefix="/protocol", tags=["protocol"])


def _parse_cn_filters(raw_values: list[str]) -> list[str]:
    cn_values: list[str] = []
    for raw_value in raw_values:
        for item in raw_value.split(","):
            value = item.strip()
            if value:
                cn_values.append(value)
    return cn_values


@router.post("/upload")
async def upload_protocol_packet(request: Request, db: Session = Depends(get_db)) -> dict:
    raw_packet = (await request.body()).decode("utf-8")
    try:
        message = parse_message(raw_packet)
    except ValueError as exc:
        create_protocol_log(
            db,
            source="http",
            raw_packet=raw_packet,
            status="rejected",
            error_message=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    normalized = normalize_hj212_message(message)
    try:
        result = ingest_payload(db, normalized.model_dump(mode="json"))
    except Exception as exc:
        db.rollback()
        create_protocol_log(
            db,
            source="http",
            raw_packet=raw_packet,
            status="ingest_failed",
            message=message,
            metric_count=len(message.metrics),
            error_message=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    ack_packet = build_data_ack(message)
    create_protocol_log(
        db,
        source="http",
        raw_packet=raw_packet,
        status="accepted",
        message=message,
        metric_count=len(message.metrics),
        ack_packet=ack_packet,
    )
    return {**result, "ackPacket": ack_packet}


@router.get("/logs")
def list_protocol_logs(
    request: Request,
    cn: str | None = Query(default=None, description="HJ212 CN. Supports comma values or repeated cn params."),
    mn: str | None = Query(default=None, description="Monitoring point identifier"),
    status: str | None = Query(default=None, description="accepted, rejected, or ingest_failed"),
    startTime: str | None = Query(default=None, description="Beijing time, ISO format"),
    endTime: str | None = Query(default=None, description="Beijing time, ISO format"),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = db.query(ProtocolUploadLog)

    raw_cn_values = request.query_params.getlist("cn") or ([cn] if cn else [])
    cn_values = _parse_cn_filters(raw_cn_values)
    if cn_values:
        query = query.filter(ProtocolUploadLog.cn.in_(cn_values))
    if mn:
        query = query.filter(ProtocolUploadLog.mn == mn)
    if status:
        query = query.filter(ProtocolUploadLog.status == status)

    start = parse_beijing_datetime(startTime)
    end = parse_beijing_datetime(endTime)
    if start is not None and end is not None and end < start:
        raise HTTPException(status_code=400, detail="结束时间不能早于开始时间")
    if start is not None:
        query = query.filter(ProtocolUploadLog.received_at >= start)
    if end is not None:
        query = query.filter(ProtocolUploadLog.received_at <= end)

    logs = query.order_by(ProtocolUploadLog.received_at.desc(), ProtocolUploadLog.id.desc()).limit(100).all()
    return [serialize_protocol_log(log) for log in logs]
