from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    contact_name: Mapped[str] = mapped_column(String(50))
    contact_phone: Mapped[str] = mapped_column(String(30))
    address: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="active")

    sheds = relationship("Shed", back_populates="farm", cascade="all, delete-orphan")
