from __future__ import annotations

from sqlalchemy import create_engine, text

from app.core.config import settings


def build_admin_url() -> str:
    return (
        f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}"
        f"@{settings.mysql_host}:{settings.mysql_port}/mysql?charset=utf8mb4"
    )


def create_database() -> None:
    engine = create_engine(build_admin_url(), isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{settings.mysql_database}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )


if __name__ == "__main__":
    create_database()
    print(f"MySQL database ready: {settings.mysql_database}")
