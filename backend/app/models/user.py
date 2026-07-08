from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str] = mapped_column(String(50))
    role: Mapped[str] = mapped_column(String(20), default="worker")
