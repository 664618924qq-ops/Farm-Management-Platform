from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    metric_code: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    metric_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quality: Mapped[str] = mapped_column(String(20), nullable=False, default="good")
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    upload_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
