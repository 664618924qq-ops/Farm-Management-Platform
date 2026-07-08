from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.services.timezone import beijing_now_naive


class ProtocolUploadLog(Base):
    __tablename__ = "protocol_upload_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default="http", index=True)
    mn: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    cn: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    qn: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="received", index=True)
    metric_count: Mapped[int] = mapped_column(Integer, default=0)
    raw_packet: Mapped[str] = mapped_column(Text)
    ack_packet: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive, index=True)
