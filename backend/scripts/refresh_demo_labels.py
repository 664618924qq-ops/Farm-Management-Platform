from __future__ import annotations

from app.db.session import SessionLocal
from app.models.alert import AlertRecord
from app.models.device import Device
from app.models.farm import Farm
from app.models.inspection import InspectionRecord
from app.models.sensor import Sensor
from app.models.shed import Shed
from app.models.telemetry import TelemetryLatest, TelemetryRecord
from app.models.user import User


def main() -> None:
    db = SessionLocal()
    try:
        farm_names = {
            "FARM-001": ("East Demo Farm", "Manager Zhang", "88 Demo Road, Jiangsu"),
            "FARM-002": ("Coastal Joint Farm", "Supervisor Li", "166 Haixing Road, Zhejiang"),
        }
        shed_names = {
            "SHED-001": "Shed 1",
            "SHED-002": "Shed 2",
            "SHED-003": "Zone A Shed",
        }
        device_names = {
            "DEV-001": "Gateway 1",
            "DEV-002": "Gateway 2",
        }
        sensor_names = {
            "temperature": "Temperature",
            "humidity": "Humidity",
            "ammonia": "Ammonia",
            "co2": "CO2",
            "illumination": "Illumination",
        }

        for farm in db.query(Farm).all():
            if farm.code in farm_names:
                farm.name, farm.contact_name, farm.address = farm_names[farm.code]

        for shed in db.query(Shed).all():
            shed.name = shed_names.get(shed.code, shed.name)

        for device in db.query(Device).all():
            device.name = device_names.get(device.code, device.name)

        for sensor in db.query(Sensor).all():
            sensor.name = sensor_names.get(sensor.code, sensor.name)

        for row in db.query(TelemetryLatest).all():
            row.sensor_name = sensor_names.get(row.sensor_code, row.sensor_name)

        for row in db.query(TelemetryRecord).all():
            row.sensor_name = sensor_names.get(row.sensor_code, row.sensor_name)

        for alert in db.query(AlertRecord).all():
            if alert.sensor_code == "ammonia":
                alert.message = "Ammonia in Shed 2 is above the warning threshold. Please inspect ventilation."

        for inspection in db.query(InspectionRecord).all():
            if inspection.inspector_name != "Tester":
                inspection.inspector_name = "Worker Wang"
                inspection.notes = "Morning inspection completed. Fans are operating normally."

        for user in db.query(User).all():
            if user.username == "admin":
                user.display_name = "System Admin"
            if user.username == "worker":
                user.display_name = "Inspection Worker"

        db.commit()
        print("Demo labels refreshed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
