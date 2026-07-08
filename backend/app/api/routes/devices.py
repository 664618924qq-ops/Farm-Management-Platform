from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.device import Device
from app.schemas.common import DevicePayload

router = APIRouter(prefix="/devices", tags=["devices"])


def serialize_device(device: Device) -> dict:
    return {
        "id": device.id,
        "farmId": device.farm_id,
        "shedId": device.shed_id,
        "code": device.code,
        "name": device.name,
        "deviceType": device.device_type,
        "protocolType": device.protocol_type,
        "connectionType": device.connection_type,
        "status": device.status,
        "configJson": device.config_json,
    }


@router.get("")
def list_devices(db: Session = Depends(get_db)) -> list[dict]:
    return [serialize_device(item) for item in db.query(Device).order_by(Device.id.asc()).all()]


@router.post("")
def create_device(payload: DevicePayload, db: Session = Depends(get_db)) -> dict:
    device = Device(**payload.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return serialize_device(device)


@router.put("/{device_id}")
def update_device(device_id: int, payload: DevicePayload, db: Session = Depends(get_db)) -> dict:
    device = db.query(Device).filter(Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    for key, value in payload.model_dump().items():
        setattr(device, key, value)
    db.commit()
    db.refresh(device)
    return serialize_device(device)


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    device = db.query(Device).filter(Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    db.delete(device)
    db.commit()
    return {"success": True}
