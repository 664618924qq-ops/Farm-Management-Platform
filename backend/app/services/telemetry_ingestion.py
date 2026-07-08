from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.alert import AlertRecord
from app.models.device import Device
from app.models.farm import Farm
from app.models.sensor import Sensor
from app.models.shed import Shed
from app.models.telemetry import TelemetryLatest, TelemetryRecord
from app.services.hj212 import HJ212Message


class MetricReading(BaseModel):
    code: str
    value: float
    unit: str
    flag: str = "N"


class NormalizedTelemetry(BaseModel):
    farm_code: str
    shed_code: str
    device_code: str
    reported_at: datetime
    command_code: str = "2011"
    metrics: list[MetricReading]


METRIC_CODE_MAP = {
    "w01010": ("Temperature", "C"),
    "w01014": ("pH", ""),
    "w01001": ("Dissolved Oxygen", "mg/L"),
    "w01017": ("Conductivity", "mS/cm"),
    "w01019": ("Salinity", "g/L"),
}


def normalize_payload(payload: dict) -> NormalizedTelemetry:
    farm_code = payload.get("farmCode", payload.get("farm_code", "AUTO-FARM"))
    shed_code = payload.get("shedCode", payload.get("shed_code", "AUTO-SHED"))
    device_code = payload.get("deviceCode", payload.get("device_code"))
    reported_at = payload.get("reportedAt", payload.get("reported_at"))
    command_code = payload.get("commandCode", payload.get("command_code", "2011"))

    if device_code is None or reported_at is None:
        raise ValueError("Payload missing required device_code or reported_at fields")

    return NormalizedTelemetry(
        farm_code=farm_code,
        shed_code=shed_code,
        device_code=device_code,
        reported_at=reported_at,
        command_code=command_code,
        metrics=[MetricReading(**item) for item in payload["metrics"]],
    )


def normalize_hj212_message(message: HJ212Message) -> NormalizedTelemetry:
    return NormalizedTelemetry(
        farm_code="AUTO-FARM",
        shed_code="AUTO-SHED",
        device_code=message.mn,
        reported_at=message.data_time,
        command_code=message.cn,
        metrics=[
            MetricReading(
                code=metric.code,
                value=metric.value,
                unit=METRIC_CODE_MAP.get(metric.code, (metric.code, ""))[1],
                flag=metric.flag,
            )
            for metric in message.metrics
        ],
    )


def _resolve_or_create_device(db: Session, normalized: NormalizedTelemetry) -> Device:
    device = db.query(Device).filter(Device.code == normalized.device_code).first()
    if device is not None:
        return device

    farm = db.query(Farm).order_by(Farm.id.asc()).first()
    shed = db.query(Shed).order_by(Shed.id.asc()).first()
    if farm is None or shed is None:
        raise ValueError("No farm or shed available for protocol device binding")

    device = Device(
        farm_id=farm.id,
        shed_id=shed.id,
        code=normalized.device_code,
        name=f"Protocol Device {normalized.device_code}",
        device_type="water_station",
        protocol_type="hj212",
        connection_type="tcp",
        status="online",
        config_json=json.dumps({"mn": normalized.device_code}),
    )
    db.add(device)
    db.flush()
    return device


def _resolve_or_create_sensor(db: Session, device: Device, metric: MetricReading) -> Sensor:
    sensor = (
        db.query(Sensor)
        .filter(Sensor.device_id == device.id, Sensor.code == metric.code)
        .first()
    )
    if sensor is not None:
        return sensor

    sensor_name, default_unit = METRIC_CODE_MAP.get(metric.code, (metric.code, metric.unit))
    sensor = Sensor(
        device_id=device.id,
        code=metric.code,
        name=sensor_name,
        unit=metric.unit or default_unit,
        lower_limit=None,
        upper_limit=None,
        sort_order=0,
    )
    db.add(sensor)
    db.flush()
    return sensor


def ingest_payload(db: Session, payload: dict) -> dict[str, str | int]:
    normalized = normalize_payload(payload)
    device = _resolve_or_create_device(db, normalized)

    for metric in normalized.metrics:
        sensor = _resolve_or_create_sensor(db, device, metric)
        sensor_name = sensor.name
        sensor_unit = metric.unit or sensor.unit

        db.add(
            TelemetryRecord(
                device_id=device.id,
                sensor_code=metric.code,
                sensor_name=sensor_name,
                value=metric.value,
                unit=sensor_unit,
                quality=metric.flag,
                command_code=normalized.command_code,
                recorded_at=normalized.reported_at,
            )
        )

        latest = (
            db.query(TelemetryLatest)
            .filter(
                TelemetryLatest.device_id == device.id,
                TelemetryLatest.sensor_code == metric.code,
            )
            .first()
        )
        if latest is None:
            latest = TelemetryLatest(
                device_id=device.id,
                sensor_code=metric.code,
                sensor_name=sensor_name,
                value=metric.value,
                unit=sensor_unit,
                quality=metric.flag,
                command_code=normalized.command_code,
                recorded_at=normalized.reported_at,
            )
            db.add(latest)
        else:
            latest.sensor_name = sensor_name
            latest.value = metric.value
            latest.unit = sensor_unit
            latest.quality = metric.flag
            latest.command_code = normalized.command_code
            latest.recorded_at = normalized.reported_at

        if sensor.upper_limit is not None and metric.value > sensor.upper_limit:
            db.add(
                AlertRecord(
                    device_id=device.id,
                    sensor_code=metric.code,
                    level="warning",
                    message=f"{sensor.name} value {metric.value}{sensor_unit} exceeded upper limit {sensor.upper_limit}{sensor_unit}",
                    status="active",
                    triggered_at=normalized.reported_at,
                )
            )

    device.status = "online"
    db.commit()
    return {
        "status": "accepted",
        "deviceId": device.id,
        "deviceCode": normalized.device_code,
        "cn": normalized.command_code,
        "metricCount": len(normalized.metrics),
    }
