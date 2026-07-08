from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FarmPayload(BaseModel):
    code: str
    name: str
    contact_name: str
    contact_phone: str
    address: str
    status: str = "active"


class ShedPayload(BaseModel):
    farm_id: int
    code: str
    name: str
    shed_type: str = "standard"
    status: str = "active"


class DevicePayload(BaseModel):
    farm_id: int
    shed_id: int
    code: str
    name: str
    device_type: str = "gateway"
    protocol_type: str = "tcp-json"
    connection_type: str = "tcp"
    status: str = "offline"
    config_json: str = "{}"


class SensorPayload(BaseModel):
    device_id: int
    code: str
    name: str
    unit: str
    lower_limit: float | None = None
    upper_limit: float | None = None
    sort_order: int = 0


class InspectionPayload(BaseModel):
    farm_id: int
    shed_id: int
    inspector_name: str
    notes: str
    status: str = "completed"


class LoginPayload(BaseModel):
    username: str
    password: str


class MetricPayload(BaseModel):
    code: str
    value: float
    unit: str


class TelemetryIngestPayload(BaseModel):
    farmCode: str
    shedCode: str
    deviceCode: str
    reportedAt: datetime
    metrics: list[MetricPayload]
