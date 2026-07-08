from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    shed_id: Mapped[int] = mapped_column(ForeignKey("sheds.id"), index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    device_type: Mapped[str] = mapped_column(String(50), default="gateway")
    protocol_type: Mapped[str] = mapped_column(String(50), default="tcp-json")
    connection_type: Mapped[str] = mapped_column(String(50), default="tcp")
    status: Mapped[str] = mapped_column(String(20), default="offline")
    config_json: Mapped[str] = mapped_column(Text, default="{}")

    shed = relationship("Shed", back_populates="devices")
    sensors = relationship("Sensor", back_populates="device", cascade="all, delete-orphan")
