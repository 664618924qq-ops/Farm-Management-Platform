from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.inspection import InspectionRecord
from app.schemas.common import InspectionPayload
from app.services.timezone import beijing_now_naive, iso_beijing

router = APIRouter(prefix="/inspections", tags=["inspections"])


STATUS_LABELS = {
    "completed": "已完成",
    "follow_up": "需跟进",
}


def _inspection_result(status: str) -> str:
    return "需跟进" if status == "follow_up" else "正常"


def _abnormal_summary(status: str, notes: str) -> str:
    if status == "follow_up":
        return notes or "存在待跟进事项"
    return "未发现明显异常"


@router.get("")
def list_inspections(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {
            "id": item.id,
            "farmId": item.farm_id,
            "shedId": item.shed_id,
            "inspectionItem": f"养殖区 {item.shed_id} 日常巡检",
            "result": _inspection_result(item.status),
            "abnormal": _abnormal_summary(item.status, item.notes),
            "handler": item.inspector_name,
            "inspectorName": item.inspector_name,
            "notes": item.notes,
            "status": item.status,
            "statusLabel": STATUS_LABELS.get(item.status, item.status),
            "createdAt": item.created_at.isoformat(),
            "createdAtBeijing": iso_beijing(item.created_at),
        }
        for item in db.query(InspectionRecord).order_by(InspectionRecord.created_at.desc()).all()
    ]


@router.post("")
def create_inspection(payload: InspectionPayload, db: Session = Depends(get_db)) -> dict:
    inspection = InspectionRecord(**payload.model_dump(), created_at=beijing_now_naive())
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    return {
        "id": inspection.id,
        "farmId": inspection.farm_id,
        "shedId": inspection.shed_id,
        "inspectionItem": f"养殖区 {inspection.shed_id} 日常巡检",
        "result": _inspection_result(inspection.status),
        "abnormal": _abnormal_summary(inspection.status, inspection.notes),
        "handler": inspection.inspector_name,
        "inspectorName": inspection.inspector_name,
        "notes": inspection.notes,
        "status": inspection.status,
        "statusLabel": STATUS_LABELS.get(inspection.status, inspection.status),
        "createdAt": inspection.created_at.isoformat(),
        "createdAtBeijing": iso_beijing(inspection.created_at),
    }
