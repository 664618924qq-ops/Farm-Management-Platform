from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.alert import AlertRecord
from app.models.device import Device
from app.models.farm import Farm
from app.models.inspection import InspectionRecord
from app.models.sensor import Sensor
from app.models.shed import Shed
from app.models.telemetry import TelemetryLatest, TelemetryRecord
from app.models.user import User


def seed_database(db: Session) -> None:
    if db.query(Farm).first():
        return

    farm = Farm(
        code="FARM-001",
        name="East Demo Farm",
        contact_name="Manager Zhang",
        contact_phone="13800000000",
        address="88 Demo Road, Jiangsu",
        status="active",
    )
    farm_two = Farm(
        code="FARM-002",
        name="Coastal Joint Farm",
        contact_name="Supervisor Li",
        contact_phone="13900000000",
        address="166 Haixing Road, Zhejiang",
        status="active",
    )
    db.add_all([farm, farm_two])
    db.flush()

    shed_one = Shed(farm_id=farm.id, code="SHED-001", name="Shed 1", shed_type="broiler", status="active")
    shed_two = Shed(farm_id=farm.id, code="SHED-002", name="Shed 2", shed_type="broiler", status="active")
    shed_three = Shed(farm_id=farm_two.id, code="SHED-003", name="Zone A Shed", shed_type="layer", status="active")
    db.add_all([shed_one, shed_two, shed_three])
    db.flush()

    device_one = Device(
        farm_id=farm.id,
        shed_id=shed_one.id,
        code="DEV-001",
        name="Gateway 1",
        device_type="gateway",
        protocol_type="tcp-json",
        connection_type="tcp",
        status="online",
        config_json='{"host":"127.0.0.1","port":9100}',
    )
    device_two = Device(
        farm_id=farm.id,
        shed_id=shed_two.id,
        code="DEV-002",
        name="Gateway 2",
        device_type="gateway",
        protocol_type="tcp-json",
        connection_type="tcp",
        status="online",
        config_json='{"host":"127.0.0.1","port":9100}',
    )
    db.add_all([device_one, device_two])
    db.flush()

    sensor_specs = [
        ("temperature", "Temperature", "C", 18, 30),
        ("humidity", "Humidity", "%", 50, 80),
        ("ammonia", "Ammonia", "ppm", 0, 15),
        ("co2", "CO2", "ppm", 0, 1200),
        ("illumination", "Illumination", "lx", 100, 500),
    ]
    sensors: list[Sensor] = []
    for device in [device_one, device_two]:
        for index, (code, name, unit, low, high) in enumerate(sensor_specs, start=1):
            sensors.append(
                Sensor(
                    device_id=device.id,
                    code=code,
                    name=name,
                    unit=unit,
                    lower_limit=low,
                    upper_limit=high,
                    sort_order=index,
                )
            )
    db.add_all(sensors)
    db.flush()

    now = datetime.now()
    base_values = {
        "temperature": 28.3,
        "humidity": 68.5,
        "ammonia": 8.2,
        "co2": 720.0,
        "illumination": 310.0,
    }
    for device in [device_one, device_two]:
        for sensor in [sensor for sensor in sensors if sensor.device_id == device.id]:
            for offset in range(12):
                value = base_values[sensor.code] + (offset % 3) * 0.4
                db.add(
                    TelemetryRecord(
                        device_id=device.id,
                        sensor_code=sensor.code,
                        sensor_name=sensor.name,
                        value=value,
                        unit=sensor.unit,
                        quality="good",
                        recorded_at=now - timedelta(hours=11 - offset),
                    )
                )
            db.add(
                TelemetryLatest(
                    device_id=device.id,
                    sensor_code=sensor.code,
                    sensor_name=sensor.name,
                    value=base_values[sensor.code],
                    unit=sensor.unit,
                    quality="good",
                    recorded_at=now,
                )
            )

    db.add(
        AlertRecord(
            device_id=device_two.id,
            sensor_code="ammonia",
            level="warning",
            message="Ammonia in Shed 2 is above the warning threshold. Please inspect ventilation.",
            status="active",
            triggered_at=now - timedelta(minutes=35),
        )
    )
    db.add(
        InspectionRecord(
            farm_id=farm.id,
            shed_id=shed_one.id,
            inspector_name="Worker Wang",
            notes="Morning inspection completed. Fans are operating normally.",
            status="completed",
            created_at=now - timedelta(hours=2),
        )
    )
    db.add_all(
        [
            User(username="admin", password="admin123", display_name="System Admin", role="admin"),
            User(username="worker", password="worker123", display_name="Inspection Worker", role="worker"),
        ]
    )
    db.commit()
