from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    site_name: Mapped[str] = mapped_column(String(100), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
