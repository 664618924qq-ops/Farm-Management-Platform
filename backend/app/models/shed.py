from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Shed(Base):
    __tablename__ = "sheds"

    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    shed_type: Mapped[str] = mapped_column(String(30), default="standard")
    status: Mapped[str] = mapped_column(String(20), default="active")

    farm = relationship("Farm", back_populates="sheds")
    devices = relationship("Device", back_populates="shed", cascade="all, delete-orphan")
