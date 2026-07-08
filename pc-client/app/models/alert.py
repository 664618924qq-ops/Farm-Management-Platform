from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    alert_code: Mapped[str] = mapped_column(String(50), nullable=False)
    alert_level: Mapped[str] = mapped_column(String(20), nullable=False)
    alert_message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
