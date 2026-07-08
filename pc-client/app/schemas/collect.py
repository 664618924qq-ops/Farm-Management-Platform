from datetime import datetime

from pydantic import BaseModel


class MetricItem(BaseModel):
    metric_code: str
    metric_name: str
    metric_value: float
    metric_unit: str | None = None
    quality: str = "good"


class CollectResponse(BaseModel):
    device_id: int
    device_code: str
    collected_at: datetime
    metrics: list[MetricItem]
