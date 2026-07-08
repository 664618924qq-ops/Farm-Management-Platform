from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CollectedMetric:
    metric_code: str
    metric_name: str
    metric_value: float
    metric_unit: str | None = None


@dataclass
class DeviceCollectResult:
    device_code: str
    collected_at: datetime
    metrics: list[CollectedMetric]


class DeviceAdapter(ABC):
    @abstractmethod
    def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_metrics(self) -> DeviceCollectResult:
        raise NotImplementedError

    @abstractmethod
    def get_status(self) -> str:
        raise NotImplementedError
