from __future__ import annotations

from sqlalchemy import inspect, text

from app.db.base import Base
from app.db.session import engine


def ensure_database_schema() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if inspector.has_table("protocol_upload_logs"):
        columns = {column["name"] for column in inspector.get_columns("protocol_upload_logs")}
        if "data_time" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE protocol_upload_logs ADD COLUMN data_time DATETIME NULL"))

    for table_name in ("telemetry_records", "telemetry_latest"):
        if not inspector.has_table(table_name):
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "command_code" not in columns:
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN command_code VARCHAR(20) DEFAULT '2011'"))

    for table_name in ("quality_rules", "quality_alert_records"):
        if not inspector.has_table(table_name):
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "standard_code" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN standard_code VARCHAR(50) NOT NULL DEFAULT 'GB3838-2002'")
                )
