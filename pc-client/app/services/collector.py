import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.alert import AlertEvent
from app.models.device import Device
from app.models.metric import DeviceMetric
from app.models.telemetry import TelemetryRecord
from app.models.upload_task import UploadTask
from app.schemas.collect import CollectResponse, MetricItem
from app.services.adapters.factory import build_adapter


ALLOWED_SAVE_INTERVAL_SECONDS = {30, 60}


def align_collected_at(collected_at: datetime, save_interval_seconds: int = 30) -> datetime:
    interval = save_interval_seconds if save_interval_seconds in ALLOWED_SAVE_INTERVAL_SECONDS else 30
    base = collected_at.replace(microsecond=0)
    floored_second = (base.second // interval) * interval
    return base.replace(second=floored_second)


def _build_alert_code(metric_code: str) -> str:
    return f"metric_threshold_{metric_code}"


def _evaluate_metric_quality(metric_value: float, metric_rule: DeviceMetric | None) -> tuple[str, str | None]:
    if metric_rule is None:
        return "good", None
    lower_limit = float(metric_rule.lower_limit) if metric_rule.lower_limit is not None else None
    upper_limit = float(metric_rule.upper_limit) if metric_rule.upper_limit is not None else None
    if lower_limit is not None and metric_value < lower_limit:
        return "warning", f"{metric_rule.metric_name} 低于下限 {lower_limit}"
    if upper_limit is not None and metric_value > upper_limit:
        return "warning", f"{metric_rule.metric_name} 高于上限 {upper_limit}"
    return "good", None


def _sync_threshold_alert(
    db: Session,
    device: Device,
    metric_code: str,
    metric_name: str,
    metric_value: float,
    metric_unit: str | None,
    quality: str,
    reason: str | None,
) -> None:
    alert_code = _build_alert_code(metric_code)
    active_alert = (
        db.query(AlertEvent)
        .filter(
            AlertEvent.device_id == device.id,
            AlertEvent.alert_code == alert_code,
            AlertEvent.status.in_(["active", "acknowledged"]),
        )
        .order_by(AlertEvent.id.desc())
        .first()
    )
    if quality != "good":
        message = f"{device.device_name} {reason or metric_name}，当前值 {metric_value}{metric_unit or ''}"
        if active_alert is None:
            db.add(
                AlertEvent(
                    device_id=device.id,
                    alert_code=alert_code,
                    alert_level="warning",
                    alert_message=message,
                    status="active",
                )
            )
        else:
            active_alert.alert_message = message
            active_alert.triggered_at = datetime.now()
        return

    if active_alert is not None:
        active_alert.status = "recovered"
        active_alert.recovered_at = datetime.now()


def _enqueue_completed_hourly_upload_task(db: Session, device: Device, current_collected_at: datetime) -> None:
    hour_start = current_collected_at.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    hour_end = hour_start + timedelta(hours=1)
    hour_bucket = hour_start.isoformat()

    existing_task = (
        db.query(UploadTask)
        .filter(UploadTask.task_type == "hourly")
        .filter(UploadTask.payload_json.contains(f'"device_id": {device.id}'))
        .filter(UploadTask.payload_json.contains(f'"hour_bucket": "{hour_bucket}"'))
        .first()
    )
    if existing_task is not None:
        return

    rows = (
        db.query(TelemetryRecord)
        .filter(
            TelemetryRecord.device_id == device.id,
            TelemetryRecord.collected_at >= hour_start,
            TelemetryRecord.collected_at < hour_end,
        )
        .order_by(TelemetryRecord.id.asc())
        .all()
    )
    if not rows:
        return

    aggregates: dict[str, dict] = {}
    for row in rows:
        current = aggregates.setdefault(
            row.metric_code,
            {
                "metric_code": row.metric_code,
                "metric_name": row.metric_name,
                "metric_unit": row.metric_unit,
                "total": 0.0,
                "count": 0,
            },
        )
        current["total"] += float(row.metric_value)
        current["count"] += 1

    metrics = []
    for current in aggregates.values():
        metrics.append(
            {
                "metric_code": current["metric_code"],
                "metric_name": current["metric_name"],
                "metric_unit": current["metric_unit"],
                "metric_value": round(current["total"] / current["count"], 3),
            }
        )

    task_payload = {
        "device_id": device.id,
        "device_code": device.device_code,
        "hour_bucket": hour_bucket,
        "collected_at": hour_start.isoformat(),
        "metrics": metrics,
    }
    db.add(UploadTask(task_type="hourly", payload_json=json.dumps(task_payload, ensure_ascii=False)))


def collect_once(db: Session, device: Device, save_interval_seconds: int = 30) -> CollectResponse:
    metric_rules = {
        row.metric_code: row
        for row in db.query(DeviceMetric).filter(DeviceMetric.device_id == device.id).all()
    }
    adapter = build_adapter(device)
    if hasattr(adapter, "set_metric_templates"):
        adapter.set_metric_templates(
            [
                {
                    "metric_code": row.metric_code,
                    "metric_name": row.metric_name,
                    "metric_unit": row.metric_unit,
                }
                for row in metric_rules.values()
            ]
        )
    adapter.connect()
    result = adapter.read_metrics()
    adapter.disconnect()
    aligned_collected_at = align_collected_at(result.collected_at, save_interval_seconds)

    metrics: list[MetricItem] = []
    metric_payloads: list[dict] = []
    quality_flags: list[dict] = []
    for metric in result.metrics:
        metric_rule = metric_rules.get(metric.metric_code)
        quality, reason = _evaluate_metric_quality(metric.metric_value, metric_rule)
        db.add(
            TelemetryRecord(
                device_id=device.id,
                metric_code=metric.metric_code,
                metric_name=metric.metric_name,
                metric_value=metric.metric_value,
                metric_unit=metric.metric_unit,
                quality=quality,
                collected_at=aligned_collected_at,
            )
        )
        _sync_threshold_alert(
            db=db,
            device=device,
            metric_code=metric.metric_code,
            metric_name=metric.metric_name,
            metric_value=metric.metric_value,
            metric_unit=metric.metric_unit,
            quality=quality,
            reason=reason,
        )
        metrics.append(
            MetricItem(
                metric_code=metric.metric_code,
                metric_name=metric.metric_name,
                metric_value=metric.metric_value,
                metric_unit=metric.metric_unit,
                quality=quality,
            )
        )
        metric_payload = {
            "metric_code": metric.metric_code,
            "metric_name": metric.metric_name,
            "metric_value": metric.metric_value,
            "metric_unit": metric.metric_unit,
            "quality": quality,
        }
        metric_payloads.append(metric_payload)
        if quality != "good":
            quality_flags.append(
                {
                    "metric_code": metric.metric_code,
                    "quality": quality,
                    "reason": reason or "本地阈值提示",
                }
            )

    task_payload = {
        "device_id": device.id,
        "device_code": device.device_code,
        "collected_at": aligned_collected_at.isoformat(),
        "metrics": metric_payloads,
        "local_analysis": {
            "quality_flags": quality_flags,
            "sms_notice_reserved": bool(quality_flags),
            "boundary": "PC only provides local hints; final alarm and SMS dispatch are handled by platform.",
        },
    }
    db.add(UploadTask(task_type="telemetry", payload_json=json.dumps(task_payload, ensure_ascii=False)))
    _enqueue_completed_hourly_upload_task(db, device, aligned_collected_at)
    db.commit()

    return CollectResponse(
        device_id=device.id,
        device_code=device.device_code,
        collected_at=aligned_collected_at,
        metrics=metrics,
    )
