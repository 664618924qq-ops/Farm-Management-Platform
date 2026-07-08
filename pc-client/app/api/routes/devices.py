from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.device import Device
from app.schemas.collect import CollectResponse
from app.services.collector import collect_once


router = APIRouter()


@router.get("")
def list_devices(db: Session = Depends(get_db)) -> list[dict]:
    devices = db.query(Device).order_by(Device.id.asc()).all()
    return [
        {
            "id": device.id,
            "device_code": device.device_code,
            "device_name": device.device_name,
            "device_type": device.device_type,
            "protocol_type": device.protocol_type,
            "connection_type": device.connection_type,
            "status": device.status,
        }
        for device in devices
    ]


@router.post("/{device_id}/collect", response_model=CollectResponse)
def collect_device(device_id: int, db: Session = Depends(get_db)) -> CollectResponse:
    device = db.query(Device).filter(Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")
    return collect_once(db=db, device=device)
