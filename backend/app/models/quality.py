from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.services.timezone import beijing_now_naive


class QualityRule(Base):
    __tablename__ = "quality_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    sensor_code: Mapped[str] = mapped_column(String(50), index=True)
    rule_type: Mapped[str] = mapped_column(String(50), index=True)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    window_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    standard_code: Mapped[str] = mapped_column(String(50), default="PROJECT_SURFACE_WATER_REQUIREMENTS", index=True)
    basis: Mapped[str] = mapped_column(Text, default="")


class QualityAlertRecord(Base):
    __tablename__ = "quality_alert_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive, index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    mn: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    sensor_code: Mapped[str] = mapped_column(String(50), index=True)
    rule_type: Mapped[str] = mapped_column(String(50), index=True)
    standard_code: Mapped[str] = mapped_column(String(50), default="PROJECT_SURFACE_WATER_REQUIREMENTS", index=True)
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_text: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    notification_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    message: Mapped[str] = mapped_column(Text, default="")


class SmsNotificationConfig(Base):
    __tablename__ = "sms_notification_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(30), index=True)
    template_code: Mapped[str] = mapped_column(String(100), default="quality_alert")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    rate_limit_minutes: Mapped[int] = mapped_column(Integer, default=30)
    remark: Mapped[str | None] = mapped_column(String(200), nullable=True)


class SmsSendLog(Base):
    __tablename__ = "sms_send_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(30), index=True)
    template_code: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="dry_run", index=True)
    provider: Mapped[str] = mapped_column(String(50), default="reserved")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
