from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "Livestock Monitoring Platform"
    api_prefix: str = "/api/v1"
    database_url: str = os.getenv(
        "APP_DATABASE_URL",
        "mysql+pymysql://root:zeei@127.0.0.1:3306/livestock_monitor?charset=utf8mb4",
    )
    mysql_host: str = os.getenv("APP_MYSQL_HOST", "127.0.0.1")
    mysql_port: int = int(os.getenv("APP_MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("APP_MYSQL_USER", "root")
    mysql_password: str = os.getenv("APP_MYSQL_PASSWORD", "zeei")
    mysql_database: str = os.getenv("APP_MYSQL_DATABASE", "livestock_monitor")
    tcp_host: str = os.getenv("APP_TCP_HOST", "127.0.0.1")
    tcp_port: int = int(os.getenv("APP_TCP_PORT", "9100"))


settings = Settings()
