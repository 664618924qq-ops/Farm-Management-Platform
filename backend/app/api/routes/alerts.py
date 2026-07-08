from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.alert import AlertRecord
from app.models.device import Device
from app.services.timezone import iso_beijing

router = APIRouter(prefix="/alerts", tags=["alerts"])


LEVEL_LABELS = {
    "info": "提示",
    "warning": "预警",
    "critical": "严重",
}

STATUS_LABELS = {
    "active": "待处理",
    "acknowledged": "已确认",
    "recovered": "已恢复",
}


def _suggestion_for(alert: AlertRecord) -> str:
    if alert.status == "acknowledged":
        return "已确认，建议持续观察后续数据是否恢复稳定。"
    if alert.level == "critical":
        return "建议立即复核现场设备和水质状态，必要时安排人员到场处理。"
    return "建议核对传感器、现场环境和近期趋势，确认是否需要处理。"


def _reason_for(alert: AlertRecord) -> str:
    if "Ammonia" in alert.message or alert.sensor_code in {"ammonia", "w21003"}:
        return "氨氮/氨气指标超过预警阈值，请关注水体或环境变化。"
    return alert.message


@router.get("")
def list_alerts(db: Session = Depends(get_db)) -> list[dict]:
    device_ids = {item.device_id for item in db.query(AlertRecord.device_id).all()} or {0}
    device_map = {device.id: device.code for device in db.query(Device).filter(Device.id.in_(device_ids)).all()}
    return [
        {
            "id": item.id,
            "deviceId": item.device_id,
            "deviceCode": device_map.get(item.device_id, f"设备 {item.device_id}"),
            "sensorCode": item.sensor_code,
            "level": item.level,
            "levelLabel": LEVEL_LABELS.get(item.level, item.level),
            "message": item.message,
            "reason": _reason_for(item),
            "suggestion": _suggestion_for(item),
            "status": item.status,
            "statusLabel": STATUS_LABELS.get(item.status, item.status),
            "triggeredAt": item.triggered_at.isoformat(),
            "triggeredAtBeijing": iso_beijing(item.triggered_at),
            "acknowledgedBy": item.acknowledged_by,
        }
        for item in db.query(AlertRecord).order_by(AlertRecord.triggered_at.desc()).all()
    ]


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)) -> dict:
    alert = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="告警不存在")
    alert.status = "acknowledged"
    alert.acknowledged_by = "demo-user"
    alert.recovered_at = datetime.now()
    db.commit()
    db.refresh(alert)
    return {"success": True, "status": alert.status}
