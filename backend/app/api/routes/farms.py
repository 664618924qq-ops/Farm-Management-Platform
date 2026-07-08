from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.farm import Farm
from app.schemas.common import FarmPayload

router = APIRouter(prefix="/farms", tags=["farms"])


def serialize_farm(farm: Farm) -> dict:
    return {
        "id": farm.id,
        "code": farm.code,
        "name": farm.name,
        "contactName": farm.contact_name,
        "contactPhone": farm.contact_phone,
        "address": farm.address,
        "status": farm.status,
    }


@router.get("")
def list_farms(db: Session = Depends(get_db)) -> list[dict]:
    return [serialize_farm(item) for item in db.query(Farm).order_by(Farm.id.asc()).all()]


@router.post("")
def create_farm(payload: FarmPayload, db: Session = Depends(get_db)) -> dict:
    farm = Farm(**payload.model_dump())
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return serialize_farm(farm)


@router.put("/{farm_id}")
def update_farm(farm_id: int, payload: FarmPayload, db: Session = Depends(get_db)) -> dict:
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if farm is None:
        raise HTTPException(status_code=404, detail="养殖场不存在")
    for key, value in payload.model_dump().items():
        setattr(farm, key, value)
    db.commit()
    db.refresh(farm)
    return serialize_farm(farm)


@router.delete("/{farm_id}")
def delete_farm(farm_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if farm is None:
        raise HTTPException(status_code=404, detail="养殖场不存在")
    db.delete(farm)
    db.commit()
    return {"success": True}
