from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.alert import AlertEvent
from app.models.device import Device
from app.models.metric import DeviceMetric
from app.models.site import Site
from app.models.telemetry import TelemetryRecord
from app.models.upload_task import UploadTask
from app.services import collector as collector_module


def test_align_collected_at_floors_to_save_interval_boundary():
    source_time = datetime(2026, 7, 2, 8, 0, 44, 321000)

    assert collector_module.align_collected_at(source_time, 30) == datetime(2026, 7, 2, 8, 0, 30)
    assert collector_module.align_collected_at(source_time, 60) == datetime(2026, 7, 2, 8, 0, 0)


class FakeAdapter:
    def __init__(self, metrics):
        self._metrics = metrics

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        return None

    def read_metrics(self):
        from app.services.adapters.base import DeviceCollectResult

        return DeviceCollectResult(
            device_code="DEV-001",
            collected_at=datetime(2026, 7, 2, 8, 0, 0),
            metrics=self._metrics,
        )

    def get_status(self) -> str:
        return "online"


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with maker() as db:
        db.add(Site(id=1, site_code="SITE-001", site_name="Test Site"))
        db.add(
            Device(
                id=1,
                site_id=1,
                pond_code="POND-01",
                device_code="DEV-001",
                device_name="测试设备1",
                device_type="water_quality",
                protocol_type="mock",
                connection_type="tcp",
                status="offline",
                sort_order=1,
                config_json="{}",
            )
        )
        db.add(
            DeviceMetric(
                device_id=1,
                metric_code="water_temp",
                metric_name="水温",
                metric_unit="C",
                lower_limit=20,
                upper_limit=32,
                register_address="40001",
                sort_order=1,
            )
        )
        db.commit()
    return maker


def test_collect_once_creates_threshold_alert(monkeypatch):
    maker = build_session()
    from app.services.adapters.base import CollectedMetric

    monkeypatch.setattr(
        collector_module,
        "build_adapter",
        lambda device: FakeAdapter([CollectedMetric(metric_code="water_temp", metric_name="水温", metric_value=35.5, metric_unit="C")]),
    )

    with maker() as db:
        device = db.query(Device).filter(Device.id == 1).first()
        result = collector_module.collect_once(db, device, save_interval_seconds=30)
        telemetry = db.query(TelemetryRecord).all()
        alerts = db.query(AlertEvent).all()
        tasks = db.query(UploadTask).all()

    assert result.device_code == "DEV-001"
    assert result.collected_at == datetime(2026, 7, 2, 8, 0, 0)
    assert len(telemetry) == 1
    assert telemetry[0].collected_at == datetime(2026, 7, 2, 8, 0, 0)
    assert '"collected_at": "2026-07-02T08:00:00"' in tasks[0].payload_json
    assert telemetry[0].quality == "warning"
    assert len(alerts) == 1
    assert alerts[0].status == "active"
    assert "高于上限" in alerts[0].alert_message
    assert len(tasks) == 1


def test_collect_once_recovers_threshold_alert(monkeypatch):
    maker = build_session()
    from app.services.adapters.base import CollectedMetric

    readings = [
        [CollectedMetric(metric_code="water_temp", metric_name="水温", metric_value=35.5, metric_unit="C")],
        [CollectedMetric(metric_code="water_temp", metric_name="水温", metric_value=28.0, metric_unit="C")],
    ]

    def adapter_factory(device):
        return FakeAdapter(readings.pop(0))

    monkeypatch.setattr(collector_module, "build_adapter", adapter_factory)

    with maker() as db:
        device = db.query(Device).filter(Device.id == 1).first()
        collector_module.collect_once(db, device)
        collector_module.collect_once(db, device)
        alerts = db.query(AlertEvent).order_by(AlertEvent.id.asc()).all()
        telemetry = db.query(TelemetryRecord).order_by(TelemetryRecord.id.asc()).all()

    assert len(alerts) == 1
    assert alerts[0].status == "recovered"
    assert alerts[0].recovered_at is not None
    assert telemetry[0].quality == "warning"
    assert telemetry[1].quality == "good"


def test_collect_once_enqueues_previous_hourly_upload_task(monkeypatch):
    maker = build_session()
    from app.services.adapters.base import CollectedMetric

    monkeypatch.setattr(
        collector_module,
        "build_adapter",
        lambda device: FakeAdapter([CollectedMetric(metric_code="water_temp", metric_name="姘存俯", metric_value=29.0, metric_unit="C")]),
    )

    with maker() as db:
        db.add(
            TelemetryRecord(
                device_id=1,
                metric_code="water_temp",
                metric_name="姘存俯",
                metric_value=28.0,
                metric_unit="C",
                quality="good",
                collected_at=datetime(2026, 7, 2, 7, 10, 0),
            )
        )
        db.add(
            TelemetryRecord(
                device_id=1,
                metric_code="water_temp",
                metric_name="姘存俯",
                metric_value=30.0,
                metric_unit="C",
                quality="good",
                collected_at=datetime(2026, 7, 2, 7, 40, 0),
            )
        )
        db.commit()

        device = db.query(Device).filter(Device.id == 1).first()
        collector_module.collect_once(db, device)
        hourly_tasks = db.query(UploadTask).filter(UploadTask.task_type == "hourly").all()

    assert len(hourly_tasks) == 1
    assert '"hour_bucket": "2026-07-02T07:00:00"' in hourly_tasks[0].payload_json
    assert '"metric_value": 29.0' in hourly_tasks[0].payload_json


def test_collect_once_uses_bound_factor_codes_for_mock_adapter():
    maker = build_session()

    with maker() as db:
        metric_rule = db.query(DeviceMetric).filter(DeviceMetric.device_id == 1).first()
        metric_rule.metric_code = "w01010"
        metric_rule.metric_name = "水温"
        metric_rule.metric_unit = "℃"
        metric_rule.lower_limit = None
        metric_rule.upper_limit = None
        db.add(
            DeviceMetric(
                device_id=1,
                metric_code="w01014",
                metric_name="溶解氧",
                metric_unit="mg/L",
                lower_limit=None,
                upper_limit=None,
                register_address="40002",
                sort_order=2,
            )
        )
        db.commit()

        device = db.query(Device).filter(Device.id == 1).first()
        result = collector_module.collect_once(db, device)
        telemetry = db.query(TelemetryRecord).order_by(TelemetryRecord.id.asc()).all()

    assert [item.metric_code for item in result.metrics] == ["w01010", "w01014"]
    assert [float(row.metric_value) for row in telemetry] == [0.0, 0.0]
    assert [row.metric_code for row in telemetry] == ["w01010", "w01014"]


def test_collect_once_enqueues_upload_task_for_first_sample():
    maker = build_session()

    with maker() as db:
        metric_rule = db.query(DeviceMetric).filter(DeviceMetric.device_id == 1).first()
        metric_rule.metric_code = "w01010"
        metric_rule.metric_name = "姘存俯"
        metric_rule.metric_unit = "鈩?"
        metric_rule.lower_limit = None
        metric_rule.upper_limit = None
        db.commit()

        device = db.query(Device).filter(Device.id == 1).first()
        collector_module.collect_once(db, device)
        tasks = db.query(UploadTask).filter(UploadTask.task_type == "telemetry").all()

    assert len(tasks) == 1


def test_collect_once_enqueues_upload_task_when_new_sample_has_same_values():
    maker = build_session()

    with maker() as db:
        metric_rule = db.query(DeviceMetric).filter(DeviceMetric.device_id == 1).first()
        metric_rule.metric_code = "w01010"
        metric_rule.metric_name = "水温"
        metric_rule.metric_unit = "℃"
        metric_rule.lower_limit = None
        metric_rule.upper_limit = None
        db.add(
            TelemetryRecord(
                device_id=1,
                metric_code="w01010",
                metric_name="水温",
                metric_value=0.0,
                metric_unit="℃",
                quality="good",
                collected_at=datetime(2026, 7, 6, 11, 0, 0),
            )
        )
        db.commit()

        device = db.query(Device).filter(Device.id == 1).first()
        before_tasks = db.query(UploadTask).count()
        collector_module.collect_once(db, device)
        after_tasks = db.query(UploadTask).count()

    assert after_tasks == before_tasks + 1
