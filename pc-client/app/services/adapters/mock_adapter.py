from datetime import datetime

from app.services.adapters.base import CollectedMetric, DeviceAdapter, DeviceCollectResult


class MockDeviceAdapter(DeviceAdapter):
    def __init__(self, device_code: str) -> None:
        self.device_code = device_code
        self.connected = False
        self.metric_templates: list[dict] = []

    def set_metric_templates(self, metric_templates: list[dict]) -> None:
        self.metric_templates = metric_templates

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def read_metrics(self) -> DeviceCollectResult:
        metrics = [
            CollectedMetric(
                metric_code=str(item.get("metric_code", "")).strip(),
                metric_name=str(item.get("metric_name", "")).strip() or str(item.get("metric_code", "")).strip(),
                metric_value=0.0,
                metric_unit=str(item.get("metric_unit", "")).strip() or None,
            )
            for item in self.metric_templates
            if str(item.get("metric_code", "")).strip()
        ]
        if not metrics:
            metrics = [
                CollectedMetric(metric_code="water_temp", metric_name="水温", metric_value=0.0, metric_unit="C"),
                CollectedMetric(metric_code="ph", metric_name="pH", metric_value=0.0, metric_unit=""),
                CollectedMetric(metric_code="do", metric_name="溶解氧", metric_value=0.0, metric_unit="mg/L"),
            ]
        return DeviceCollectResult(
            device_code=self.device_code,
            collected_at=datetime.now(),
            metrics=metrics,
        )

    def get_status(self) -> str:
        return "online" if self.connected else "offline"
