from __future__ import annotations

from collections import defaultdict
from statistics import mean

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.device import Device
from app.models.quality import QualityAlertRecord
from app.models.telemetry import TelemetryRecord
from app.services.thresholds import PRIMARY_STANDARD_CODE, evaluate_threshold
from app.services.timezone import iso_beijing, parse_beijing_datetime

router = APIRouter(prefix="/data", tags=["data"])


def _query_records(
    db: Session,
    *,
    command_code: str,
    mn: str | None,
    start_time: str | None,
    end_time: str | None,
    sensor_codes: list[str],
    limit: int,
) -> list[TelemetryRecord]:
    query = db.query(TelemetryRecord).join(Device, Device.id == TelemetryRecord.device_id)
    query = query.filter(TelemetryRecord.command_code == command_code)
    if mn:
        query = query.filter(Device.code == mn)
    if sensor_codes:
        query = query.filter(TelemetryRecord.sensor_code.in_(sensor_codes))

    start = parse_beijing_datetime(start_time)
    end = parse_beijing_datetime(end_time)
    if start is not None:
        query = query.filter(TelemetryRecord.recorded_at >= start)
    if end is not None:
        query = query.filter(TelemetryRecord.recorded_at <= end)

    return query.order_by(TelemetryRecord.recorded_at.desc(), TelemetryRecord.id.desc()).limit(limit).all()


def _parse_sensor_codes(sensor_code: str | None) -> list[str]:
    if not sensor_code:
        return []
    return [item.strip() for item in sensor_code.split(",") if item.strip()]


def _history_values(db: Session, record: TelemetryRecord) -> list[float]:
    rows = (
        db.query(TelemetryRecord.value)
        .filter(
            TelemetryRecord.device_id == record.device_id,
            TelemetryRecord.sensor_code == record.sensor_code,
            TelemetryRecord.recorded_at <= record.recorded_at,
        )
        .order_by(TelemetryRecord.recorded_at.desc(), TelemetryRecord.id.desc())
        .limit(8)
        .all()
    )
    return list(reversed([float(item[0]) for item in rows]))


def _serialize_record(record: TelemetryRecord, db: Session, device_code: str | None = None) -> dict:
    quality_result = evaluate_threshold(record.sensor_code, record.value, _history_values(db, record))
    return {
        "id": record.id,
        "deviceId": record.device_id,
        "mn": device_code,
        "sensorCode": record.sensor_code,
        "sensorName": record.sensor_name,
        "value": record.value,
        "unit": record.unit,
        "quality": record.quality,
        "commandCode": record.command_code,
        "recordedAt": record.recorded_at.isoformat(),
        "recordedAtBeijing": iso_beijing(record.recorded_at),
        "qualityLabel": quality_result["qualityLabel"],
        "qualityRuleType": quality_result["ruleType"],
        "qualityMessage": quality_result["message"],
        "qualityBasis": quality_result["basis"],
        "standardCode": quality_result.get("standardCode", PRIMARY_STANDARD_CODE),
        "threshold": quality_result["threshold"],
        "dataSource": "database",
    }


@router.get("/query")
def query_data(
    cn: str = Query("2011", pattern="^(2011|2061)$"),
    mn: str | None = None,
    startTime: str | None = None,
    endTime: str | None = None,
    sensorCode: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> dict:
    records = _query_records(
        db,
        command_code=cn,
        mn=mn,
        start_time=startTime,
        end_time=endTime,
        sensor_codes=_parse_sensor_codes(sensorCode),
        limit=limit,
    )
    device_ids = {item.device_id for item in records} or {0}
    device_codes = {device.id: device.code for device in db.query(Device).filter(Device.id.in_(device_ids)).all()}
    return {
        "cn": cn,
        "mode": "实时数据查询" if cn == "2011" else "小时数据查询",
        "timeSemantics": "采集时刻" if cn == "2011" else "监测时段/小时统计",
        "timezone": "Asia/Shanghai",
        "dataSource": "database",
        "items": [_serialize_record(item, db, device_codes.get(item.device_id)) for item in records],
    }


@router.get("/analysis")
def analyze_data(
    mn: str | None = None,
    startTime: str | None = None,
    endTime: str | None = None,
    sensorCode: str | None = None,
    cn: str = Query("2011", pattern="^(2011|2061)$"),
    limit: int = Query(300, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> dict:
    records = list(
        reversed(
            _query_records(
                db,
                command_code=cn,
                mn=mn,
                start_time=startTime,
                end_time=endTime,
                sensor_codes=_parse_sensor_codes(sensorCode),
                limit=limit,
            )
        )
    )
    grouped: dict[str, list[TelemetryRecord]] = defaultdict(list)
    for record in records:
        grouped[record.sensor_code].append(record)

    series = []
    findings = []
    for code, items in grouped.items():
        values = [item.value for item in items]
        latest = items[-1]
        threshold_result = evaluate_threshold(code, latest.value, values)
        standard_code = threshold_result.get("standardCode", PRIMARY_STANDARD_CODE)
        if threshold_result["level"] != "normal":
            existing = (
                db.query(QualityAlertRecord)
                .filter(
                    QualityAlertRecord.device_id == latest.device_id,
                    QualityAlertRecord.sensor_code == code,
                    QualityAlertRecord.rule_type == threshold_result["ruleType"],
                    QualityAlertRecord.triggered_at == latest.recorded_at,
                )
                .first()
            )
            if existing is None:
                db.add(
                    QualityAlertRecord(
                        triggered_at=latest.recorded_at,
                        device_id=latest.device_id,
                        mn=None,
                        sensor_code=code,
                        rule_type=threshold_result["ruleType"],
                        standard_code=standard_code,
                        current_value=latest.value,
                        threshold_text=str(threshold_result["threshold"] or ""),
                        status="active",
                        notification_status="reserved",
                        message=threshold_result["message"],
                    )
                )
            findings.append(
                {
                    "sensorCode": code,
                    "sensorName": latest.sensor_name,
                    "latestValue": latest.value,
                    "unit": latest.unit,
                    **threshold_result,
                }
            )
        series.append(
            {
                "sensorCode": code,
                "sensorName": latest.sensor_name,
                "unit": latest.unit,
                "min": min(values),
                "max": max(values),
                "avg": round(mean(values), 3),
                "points": [{"time": iso_beijing(item.recorded_at), "value": item.value} for item in items],
                "threshold": threshold_result["threshold"],
                "basis": threshold_result["basis"],
                "standardCode": standard_code,
            }
        )

    db.commit()
    return {
        "cn": cn,
        "timezone": "Asia/Shanghai",
        "dataSource": "database",
        "summary": {
            "recordCount": len(records),
            "sensorCount": len(grouped),
            "findingCount": len(findings),
        },
        "series": series,
        "findings": findings,
        "suggestions": [
            "先核对传感器校准与采样时间，再结合趋势判断是否需要现场复核。",
            "主依据为本项目地表水技术要求目录及系统可配置阈值，页面建议不作为不可修改的绝对诊断。",
            "GB 11607-1989 仅作为特定渔业/养殖场景辅助参考，不作为默认主标准。",
        ],
    }
