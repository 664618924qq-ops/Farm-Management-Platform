from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    sensor_code: Mapped[str] = mapped_column(String(50), index=True)
    sensor_name: Mapped[str] = mapped_column(String(50))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    quality: Mapped[str] = mapped_column(String(20), default="good")
    command_code: Mapped[str] = mapped_column(String(20), default="2011", index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class TelemetryLatest(Base):
    __tablename__ = "telemetry_latest"
    __table_args__ = (UniqueConstraint("device_id", "sensor_code", name="uq_device_sensor_latest"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    sensor_code: Mapped[str] = mapped_column(String(50))
    sensor_name: Mapped[str] = mapped_column(String(50))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    quality: Mapped[str] = mapped_column(String(20), default="good")
    command_code: Mapped[str] = mapped_column(String(20), default="2011", index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, index=True)
