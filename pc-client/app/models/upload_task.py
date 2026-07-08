from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UploadTask(Base):
    __tablename__ = "upload_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
