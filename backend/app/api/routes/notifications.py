from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.quality import SmsNotificationConfig, SmsSendLog

router = APIRouter(prefix="/notifications", tags=["notifications"])


class SmsConfigPayload(BaseModel):
    phoneNumber: str
    templateCode: str = "quality_alert"
    enabled: bool = False
    rateLimitMinutes: int = 30
    remark: str | None = None


class SmsTestPayload(BaseModel):
    phoneNumber: str
    templateCode: str = "quality_alert"
    content: str = "平台短信通知预留测试：当前未绑定具体短信服务商。"


@router.get("/sms-configs")
def list_sms_configs(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {
            "id": item.id,
            "phoneNumber": item.phone_number,
            "templateCode": item.template_code,
            "enabled": item.enabled,
            "rateLimitMinutes": item.rate_limit_minutes,
            "remark": item.remark,
        }
        for item in db.query(SmsNotificationConfig).order_by(SmsNotificationConfig.id.desc()).all()
    ]


@router.post("/sms-configs")
def create_sms_config(payload: SmsConfigPayload, db: Session = Depends(get_db)) -> dict:
    item = SmsNotificationConfig(
        phone_number=payload.phoneNumber,
        template_code=payload.templateCode,
        enabled=payload.enabled,
        rate_limit_minutes=payload.rateLimitMinutes,
        remark=payload.remark,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "status": "saved"}


@router.post("/sms-test")
def send_sms_test(payload: SmsTestPayload, db: Session = Depends(get_db)) -> dict:
    log = SmsSendLog(
        phone_number=payload.phoneNumber,
        template_code=payload.templateCode,
        content=payload.content,
        status="dry_run",
        provider="reserved",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {
        "status": "dry_run",
        "message": "短信服务商尚未绑定，本次仅记录测试发送日志，不会产生资费。",
        "logId": log.id,
    }
