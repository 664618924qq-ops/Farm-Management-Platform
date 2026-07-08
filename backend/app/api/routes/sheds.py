from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.shed import Shed
from app.schemas.common import ShedPayload

router = APIRouter(prefix="/sheds", tags=["sheds"])


def serialize_shed(shed: Shed) -> dict:
    return {
        "id": shed.id,
        "farmId": shed.farm_id,
        "code": shed.code,
        "name": shed.name,
        "shedType": shed.shed_type,
        "status": shed.status,
    }


@router.get("")
def list_sheds(db: Session = Depends(get_db)) -> list[dict]:
    return [serialize_shed(item) for item in db.query(Shed).order_by(Shed.id.asc()).all()]


@router.post("")
def create_shed(payload: ShedPayload, db: Session = Depends(get_db)) -> dict:
    shed = Shed(**payload.model_dump())
    db.add(shed)
    db.commit()
    db.refresh(shed)
    return serialize_shed(shed)


@router.put("/{shed_id}")
def update_shed(shed_id: int, payload: ShedPayload, db: Session = Depends(get_db)) -> dict:
    shed = db.query(Shed).filter(Shed.id == shed_id).first()
    if shed is None:
        raise HTTPException(status_code=404, detail="栋舍不存在")
    for key, value in payload.model_dump().items():
        setattr(shed, key, value)
    db.commit()
    db.refresh(shed)
    return serialize_shed(shed)


@router.delete("/{shed_id}")
def delete_shed(shed_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    shed = db.query(Shed).filter(Shed.id == shed_id).first()
    if shed is None:
        raise HTTPException(status_code=404, detail="栋舍不存在")
    db.delete(shed)
    db.commit()
    return {"success": True}
