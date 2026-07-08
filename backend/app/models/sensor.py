from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    code: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(50))
    unit: Mapped[str] = mapped_column(String(20))
    lower_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0)

    device = relationship("Device", back_populates="sensors")
