from __future__ import annotations

from datetime import datetime, timedelta, timezone

BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now_naive() -> datetime:
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)


def attach_beijing(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=BEIJING_TZ)
    return value.astimezone(BEIJING_TZ)


def iso_beijing(value: datetime | None) -> str | None:
    converted = attach_beijing(value)
    return converted.isoformat() if converted else None


def parse_beijing_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    else:
        parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(BEIJING_TZ).replace(tzinfo=None)
