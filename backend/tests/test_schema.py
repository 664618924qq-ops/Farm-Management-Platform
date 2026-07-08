from sqlalchemy import inspect, text

from app.db.base import Base
from app.db.schema import ensure_database_schema
from app.db.session import engine


def test_schema_upgrade_adds_protocol_data_time_to_legacy_table() -> None:
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE protocol_upload_logs (
                    id INTEGER PRIMARY KEY,
                    source VARCHAR(20),
                    raw_packet TEXT,
                    status VARCHAR(20),
                    metric_count INTEGER,
                    received_at DATETIME
                )
                """
            )
        )

    ensure_database_schema()

    columns = {column["name"] for column in inspect(engine).get_columns("protocol_upload_logs")}
    assert "data_time" in columns


def test_schema_upgrade_is_safe_for_clean_database() -> None:
    Base.metadata.drop_all(bind=engine)

    ensure_database_schema()
    ensure_database_schema()

    columns = [column["name"] for column in inspect(engine).get_columns("protocol_upload_logs")]
    assert columns.count("data_time") == 1
