from pathlib import Path

from dotenv import dotenv_values, set_key
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "养虾监测边缘服务"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_db: str = "shrimp_monitor"
    mysql_user: str = "root"
    mysql_password: str = "123456"

    platform_host: str = "127.0.0.1"
    platform_port: int = 9100
    platform_ack_timeout_seconds: float = 3.0
    site_code: str = "SITE-001"
    gateway_code: str = "A110000_0001"

    model_config = SettingsConfigDict(env_file=str(ENV_FILE_PATH), env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4"
        )


settings = Settings()


def _parse_legacy_platform_url(url: str) -> tuple[str, int]:
    normalized = url.strip()
    if not normalized:
        return settings.platform_host, settings.platform_port
    normalized = normalized.replace("https://", "").replace("http://", "")
    host_port = normalized.split("/", 1)[0]
    if ":" in host_port:
        host, port_text = host_port.rsplit(":", 1)
        try:
            return host.strip(), int(port_text.strip())
        except ValueError:
            return host.strip(), settings.platform_port
    return host_port.strip(), settings.platform_port


def fetch_platform_env_settings() -> dict:
    values = dotenv_values(ENV_FILE_PATH)
    host = values.get("PLATFORM_HOST")
    port = values.get("PLATFORM_PORT")
    legacy_url = values.get("PLATFORM_BASE_URL")
    if (not host or not port) and legacy_url:
        host, legacy_port = _parse_legacy_platform_url(legacy_url)
        port = str(legacy_port)
    return {
        "platform_host": host or settings.platform_host,
        "platform_port": int(port or settings.platform_port),
        "site_code": values.get("SITE_CODE", settings.site_code),
        "gateway_code": values.get("GATEWAY_CODE", settings.gateway_code),
    }


def save_platform_env_settings(platform_host: str, platform_port: int, site_code: str, gateway_code: str) -> dict:
    payload = {
        "PLATFORM_HOST": platform_host.strip(),
        "PLATFORM_PORT": str(int(platform_port)),
        "SITE_CODE": site_code.strip(),
        "GATEWAY_CODE": gateway_code.strip(),
    }
    if not payload["PLATFORM_HOST"]:
        raise ValueError("平台 IP 不能为空")
    if int(payload["PLATFORM_PORT"]) <= 0:
        raise ValueError("平台端口必须大于 0")
    if not payload["SITE_CODE"]:
        raise ValueError("站点编码不能为空")
    if not payload["GATEWAY_CODE"]:
        raise ValueError("网关编码不能为空")

    for key, value in payload.items():
        set_key(str(ENV_FILE_PATH), key, value)

    settings.platform_host = payload["PLATFORM_HOST"]
    settings.platform_port = int(payload["PLATFORM_PORT"])
    settings.site_code = payload["SITE_CODE"]
    settings.gateway_code = payload["GATEWAY_CODE"]

    return {
        "platform_host": settings.platform_host,
        "platform_port": settings.platform_port,
        "site_code": settings.site_code,
        "gateway_code": settings.gateway_code,
    }
