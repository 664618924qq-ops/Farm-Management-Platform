from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    setting_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    setting_name: Mapped[str] = mapped_column(String(100), nullable=False)
    setting_group: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
