from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), nullable=False)
    pond_code: Mapped[str] = mapped_column(String(50), nullable=False)
    device_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    device_name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)
    protocol_type: Mapped[str] = mapped_column(String(50), nullable=False)
    connection_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offline")
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
