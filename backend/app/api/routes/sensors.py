from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sensor import Sensor
from app.schemas.common import SensorPayload

router = APIRouter(prefix="/sensors", tags=["sensors"])


def serialize_sensor(sensor: Sensor) -> dict:
    return {
        "id": sensor.id,
        "deviceId": sensor.device_id,
        "code": sensor.code,
        "name": sensor.name,
        "unit": sensor.unit,
        "lowerLimit": sensor.lower_limit,
        "upperLimit": sensor.upper_limit,
        "sortOrder": sensor.sort_order,
    }


@router.get("")
def list_sensors(db: Session = Depends(get_db)) -> list[dict]:
    return [serialize_sensor(item) for item in db.query(Sensor).order_by(Sensor.id.asc()).all()]


@router.post("")
def create_sensor(payload: SensorPayload, db: Session = Depends(get_db)) -> dict:
    sensor = Sensor(**payload.model_dump())
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    return serialize_sensor(sensor)


@router.put("/{sensor_id}")
def update_sensor(sensor_id: int, payload: SensorPayload, db: Session = Depends(get_db)) -> dict:
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if sensor is None:
        raise HTTPException(status_code=404, detail="传感器不存在")
    for key, value in payload.model_dump().items():
        setattr(sensor, key, value)
    db.commit()
    db.refresh(sensor)
    return serialize_sensor(sensor)


@router.delete("/{sensor_id}")
def delete_sensor(sensor_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if sensor is None:
        raise HTTPException(status_code=404, detail="传感器不存在")
    db.delete(sensor)
    db.commit()
    return {"success": True}
