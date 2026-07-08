from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.alert import AlertEvent
from app.models.device import Device
from app.models.metric import DeviceMetric
from app.models.site import Site
from app.models.system_setting import SystemSetting
from app.models.telemetry import TelemetryRecord
from app.models.upload_task import UploadTask
from desktop_app.services import data_service as service_module
from desktop_app.services.data_service import DesktopDataService


@dataclass
class FakeMetric:
    metric_code: str
    metric_name: str
    metric_value: float
    metric_unit: str | None = None


@dataclass
class FakeCollectResult:
    device_id: int
    device_code: str
    collected_at: datetime
    metrics: list[FakeMetric]


class DummySessionFactory:
    def __init__(self, maker):
        self._maker = maker

    def __call__(self):
        return self._maker()


def build_test_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with maker() as db:
        db.add(Site(id=1, site_code="SITE-001", site_name="Test Site"))
        db.add(Device(id=1, site_id=1, pond_code="POND-01", device_code="DEV-001", device_name="测试设备1", device_type="water_quality", protocol_type="mock", connection_type="tcp", status="offline", sort_order=1, config_json="{}"))
        db.add(Device(id=2, site_id=1, pond_code="POND-02", device_code="DEV-002", device_name="测试设备2", device_type="water_quality", protocol_type="mock", connection_type="tcp", status="offline", sort_order=2, config_json="{}"))
        db.add(DeviceMetric(device_id=1, metric_code="w01010", metric_name="水温", metric_unit="℃", lower_limit=20, upper_limit=32, register_address="40001", sort_order=1))
        db.add(DeviceMetric(device_id=1, metric_code="w01001", metric_name="pH", metric_unit="无量纲", lower_limit=7, upper_limit=8.8, register_address="40002", sort_order=2))
        db.add(SystemSetting(setting_key="auto_save_enabled", setting_value="1", setting_name="启用实时入库", setting_group="runtime"))
        db.add(SystemSetting(setting_key="save_interval_seconds", setting_value="30", setting_name="实时保存间隔", setting_group="runtime"))
        db.add(TelemetryRecord(device_id=1, metric_code="water_temp", metric_name="水温", metric_value=28.5, metric_unit="C", quality="good"))
        db.add(AlertEvent(device_id=1, alert_code="metric_threshold_water_temp", alert_level="warning", alert_message="水温偏高", status="active"))
        db.add(AlertEvent(device_id=1, alert_code="metric_threshold_do", alert_level="warning", alert_message="溶解氧已恢复", status="recovered"))
        db.add(UploadTask(task_type="telemetry", payload_json='{"device_id": 1}', status="failed", retry_count=5, last_error="timeout"))
        db.commit()

    return DummySessionFactory(maker)


def test_runtime_settings_can_be_saved(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    before = service.fetch_runtime_settings()
    assert before.auto_save_enabled is True
    assert before.save_interval_seconds == 30
    after = service.save_runtime_settings(False, 60)
    assert after.auto_save_enabled is False
    assert after.save_interval_seconds == 60


def test_runtime_settings_rejects_non_dropdown_interval(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()

    try:
        service.save_runtime_settings(True, 45)
    except ValueError as exc:
        assert "30 秒或 60 秒" in str(exc)
    else:
        raise AssertionError("expected non-dropdown interval to be rejected")


def test_runtime_settings_normalizes_legacy_interval_to_dropdown_value(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    with session_factory() as db:
        row = db.query(SystemSetting).filter(SystemSetting.setting_key == "save_interval_seconds").first()
        row.setting_value = "45"
        db.commit()

    service = DesktopDataService()
    settings = service.fetch_runtime_settings()
    assert settings.save_interval_seconds == 30


def test_runtime_settings_default_interval_is_30_seconds(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(service_module, "SessionLocal", DummySessionFactory(maker))
    service = DesktopDataService()
    settings = service.fetch_runtime_settings()
    assert settings.save_interval_seconds == 30


def test_platform_settings_delegate(monkeypatch):
    monkeypatch.setattr(service_module, "fetch_platform_env_settings", lambda: {"platform_host": "192.168.1.9", "platform_port": 9001, "site_code": "SITE-9", "gateway_code": "GW-9"})
    monkeypatch.setattr(service_module, "save_platform_env_settings", lambda host, port, site, gateway: {"platform_host": host, "platform_port": port, "site_code": site, "gateway_code": gateway})
    service = DesktopDataService()
    fetched = service.fetch_platform_settings()
    assert fetched.platform_host == "192.168.1.9"
    saved = service.save_platform_settings("10.0.0.8", 7000, "S1", "G1")
    assert saved.platform_port == 7000


def test_platform_connection_rejects_missing_host(monkeypatch):
    monkeypatch.setattr(service_module, "fetch_platform_env_settings", lambda: {"platform_host": "", "platform_port": 9000, "site_code": "SITE-001", "gateway_code": "GW-001"})
    service = DesktopDataService()
    result = service.test_platform_connection()
    assert result.success is False
    assert result.status == "config_error"


def test_platform_connection_accepts_reachable_tcp(monkeypatch):
    monkeypatch.setattr(service_module, "fetch_platform_env_settings", lambda: {"platform_host": "127.0.0.1", "platform_port": 9000, "site_code": "SITE-9", "gateway_code": "GW-9"})

    class DummySocket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(service_module.socket, "create_connection", lambda *args, **kwargs: DummySocket())
    service = DesktopDataService()
    result = service.test_platform_connection()
    assert result.success is True
    assert result.status == "reachable"


def test_fetch_acquisition_profiles_returns_modbus_templates(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    profiles = service.fetch_acquisition_profiles()
    protocols = [profile.protocol_type for profile in profiles]
    assert "modbus_tcp" in protocols
    assert "modbus_rtu" in protocols


def test_save_acquisition_profile_supports_register_mapping(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    profiles = service.save_acquisition_profile(
        "RTU模板A",
        "modbus_rtu",
        "serial",
        "默认串口1",
        8,
        "float32",
        "30011",
        True,
    )
    current = {profile.profile_name: profile for profile in profiles}
    assert current["RTU模板A"].is_default is True
    assert current["RTU模板A"].serial_profile_name == "默认串口1"
    assert current["RTU模板A"].register_address == "30011"


def test_serial_profiles_support_crud(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    profiles = service.save_serial_profile("2号串口", "COM2", 9600, 8, "N", 1, 2, False)
    assert any(profile.profile_name == "2号串口" for profile in profiles)
    profiles = service.save_serial_profile("2号串口A", "COM3", 19200, 8, "E", 1, 3, True, original_name="2号串口")
    current = {profile.profile_name: profile for profile in profiles}
    assert current["2号串口A"].port_name == "COM3"
    assert current["2号串口A"].is_default is True
    profiles = service.delete_serial_profile("2号串口A")
    assert all(profile.profile_name != "2号串口A" for profile in profiles)


def test_acquisition_profiles_support_delete(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    profiles = service.save_acquisition_profile(
        "TCP模板A",
        "modbus_tcp",
        "tcp",
        "",
        6,
        "float32",
        "40011",
        False,
    )
    assert any(profile.profile_name == "TCP模板A" for profile in profiles)
    profiles = service.delete_acquisition_profile("TCP模板A")
    assert all(profile.profile_name != "TCP模板A" for profile in profiles)


def test_modbus_rtu_profile_requires_serial_binding(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    try:
        service.save_acquisition_profile(
            "RTU模板B",
            "modbus_rtu",
            "serial",
            "",
            5,
            "float32",
            "30021",
            False,
        )
    except ValueError as exc:
        assert "绑定串口配置名称" in str(exc)
    else:
        raise AssertionError("expected modbus_rtu profile to require serial binding")


def test_create_device_supports_custom_model(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    created = service.create_device({"site_id": 1, "pond_code": "POND-03", "device_code": "DEV-003", "device_name": "新设备", "device_type": "vendor-x-900", "protocol_type": "custom", "connection_type": "tcp", "sort_order": 3, "config_json": '{"driver": "vendor_x"}'})
    assert created["device_type"] == "vendor-x-900"
    assert created["protocol_type"] == "custom"


def test_site_crud_supports_settings_management(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    created = service.create_site({"site_code": "SITE-002", "site_name": "Second Site", "contact_name": "Li", "contact_phone": "13800138000"})
    assert created["site_code"] == "SITE-002"
    updated = service.update_site(created["id"], {"site_code": "SITE-002A", "site_name": "Second Site A", "contact_name": "Wang", "contact_phone": "13900139000"})
    assert updated["site_name"] == "Second Site A"
    service.delete_site(created["id"])
    rows = service.fetch_sites()
    assert all(row["site_code"] != "SITE-002A" for row in rows)


def test_factor_catalog_can_be_saved(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    catalog = service.save_factor_catalog(
        [
            {"code": "water_temp", "name": "水温", "unit": "C"},
            {"code": "chlorophyll", "name": "叶绿素", "unit": "ug/L"},
        ]
    )
    codes = [item["code"] for item in catalog]
    assert "chlorophyll" in codes


def test_service_bootstrap_normalizes_legacy_factor_bindings(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    with session_factory() as db:
        db.add(DeviceMetric(device_id=2, metric_code="water_temp", metric_name="水温", metric_unit="C", lower_limit=None, upper_limit=None, register_address="40001", sort_order=1))
        db.add(DeviceMetric(device_id=2, metric_code="ph", metric_name="pH", metric_unit="", lower_limit=None, upper_limit=None, register_address="40002", sort_order=2))
        db.add(DeviceMetric(device_id=2, metric_code="do", metric_name="溶解氧", metric_unit="mg/L", lower_limit=None, upper_limit=None, register_address="40003", sort_order=3))
        db.commit()

    service = DesktopDataService()
    rows = service.fetch_device_metrics(2)
    assert [row["metric_code"] for row in rows] == ["w01010", "w01001", "w01014"]


def test_factor_catalog_rejects_duplicate_code(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    try:
        service.save_factor_catalog(
            [
                {"code": "water_temp", "name": "水温", "unit": "C"},
                {"code": "water_temp", "name": "重复水温", "unit": "C"},
            ]
        )
    except ValueError as exc:
        assert "不能重复" in str(exc)
    else:
        raise AssertionError("expected duplicate factor code to be rejected")


def test_delete_site_rejects_bound_devices(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    try:
        service.delete_site(1)
    except ValueError as exc:
        assert "关联设备" in str(exc)
    else:
        raise AssertionError("expected delete_site to reject bound devices")


def test_query_telemetry_filters_by_pond_and_metric(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    with session_factory() as db:
        db.add(TelemetryRecord(device_id=2, metric_code="do", metric_name="溶解氧", metric_value=6.2, metric_unit="mg/L", quality="good", collected_at=datetime.now()))
        db.commit()
    rows = service.query_telemetry(pond_code="POND-02", metric_keyword="溶解氧")
    assert len(rows) == 1
    assert rows[0]["device_code"] == "DEV-002"


def test_save_factor_bindings_can_create_update_delete(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    current = service.fetch_device_metrics(1)
    updated = service.save_factor_bindings(
        1,
        [
            {
                "id": current[0]["id"],
                "metric_code": "w01010",
                "lower_limit": "22",
                "upper_limit": "31",
            },
            {
                "id": "",
                "metric_code": "w01014",
                "lower_limit": "",
                "upper_limit": "",
            },
        ],
    )
    codes = [row["metric_code"] for row in updated]
    assert "w01010" in codes
    assert "w01014" in codes
    assert "w01001" not in codes


def test_fetch_devices_includes_freshness_status(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    with session_factory() as db:
        current = db.query(TelemetryRecord).first()
        current.collected_at = datetime.now()
        db.add(TelemetryRecord(device_id=2, metric_code="water_temp", metric_name="水温", metric_value=28.1, metric_unit="C", quality="good", collected_at=datetime.now() - timedelta(minutes=10)))
        db.commit()
    devices = service.fetch_devices()
    rows = {row["device_code"]: row for row in devices}
    assert rows["DEV-001"]["status"] == "online"
    assert rows["DEV-002"]["status"] == "stale"


def test_copy_device_configuration_reuses_protocol_and_config(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    service.update_device(
        1,
        {
            "pond_code": "POND-01",
            "device_name": "Template Device",
            "device_type": "vendor-pro",
            "protocol_type": "modbus_tcp",
            "connection_type": "tcp",
            "sort_order": 1,
            "config_json": '{"host": "192.168.1.20", "port": 502, "slave": 1}',
        },
    )
    copied = service.copy_device_configuration(1, 2)
    assert copied["device_type"] == "vendor-pro"
    assert copied["protocol_type"] == "modbus_tcp"
    assert '"host": "192.168.1.20"' in copied["config_json"]


def test_copy_factor_bindings_replaces_target_rows(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    service.save_factor_bindings(
        2,
        [
            {
                "id": "",
                "metric_code": "w01013",
                "lower_limit": "",
                "upper_limit": "",
            }
        ],
    )
    copied = service.copy_factor_bindings(1, 2)
    codes = [row["metric_code"] for row in copied]
    assert "w01010" in codes
    assert "w01001" in codes
    assert "w01013" not in codes


def test_update_device_persists_device_type(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    updated = service.update_device(1, {"site_id": 1, "pond_code": "POND-09", "device_name": "新设备名", "device_type": "vendor-pro", "protocol_type": "modbus_tcp", "connection_type": "serial", "sort_order": 9, "config_json": '{"port": 3}'})
    assert updated["device_type"] == "vendor-pro"


def test_modbus_tcp_connection_test_detects_missing_fields(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    service.update_device(1, {"pond_code": "POND-01", "device_name": "测试设备1", "device_type": "water_quality", "protocol_type": "modbus_tcp", "connection_type": "tcp", "sort_order": 1, "config_json": '{"host": "192.168.1.50"}'})
    result = service.test_device_connection(1)
    assert result.success is False
    assert result.status == "config_error"


def test_custom_device_connection_reports_extensible(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    service.update_device(2, {"pond_code": "POND-02", "device_name": "测试设备2", "device_type": "vendor-x", "protocol_type": "custom", "connection_type": "tcp", "sort_order": 2, "config_json": '{"driver": "vendor_x"}'})
    result = service.test_device_connection(2)
    assert result.success is True
    assert result.status == "extensible"


def test_auto_collect_all_devices_updates_status(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    monkeypatch.setattr(service_module, "collect_once", lambda db, device: FakeCollectResult(device.id, device.device_code, datetime(2026, 7, 1, 12, 0, 0), [FakeMetric("water_temp", "水温", 28.5, "C"), FakeMetric("ph", "pH", 7.8, "")]))
    service = DesktopDataService()
    result = service.auto_collect_all_devices()
    assert result["device_count"] == 1


def test_auto_collect_passes_runtime_interval_to_collector(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    with session_factory() as db:
        row = db.query(SystemSetting).filter(SystemSetting.setting_key == "save_interval_seconds").first()
        row.setting_value = "60"
        db.commit()

    captured = {}

    def fake_collect_once(db, device, save_interval_seconds=30):
        captured["save_interval_seconds"] = save_interval_seconds
        return FakeCollectResult(device.id, device.device_code, datetime(2026, 7, 1, 12, 0, 0), [FakeMetric("water_temp", "水温", 28.5, "C")])

    monkeypatch.setattr(service_module, "collect_once", fake_collect_once)
    service = DesktopDataService()
    service.auto_collect_all_devices()

    assert captured["save_interval_seconds"] == 60


def test_auto_collect_all_devices_uploads_pending_tasks_after_collect(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    upload_calls: list[dict] = []

    def fake_upload_pending_records(db, *, task_ids=None, max_tasks=20):
        upload_calls.append({"called": True, "task_ids": list(task_ids or [])})
        return {"success": True, "processed": 1, "uploaded": 1, "failed": 0}

    monkeypatch.setattr(service_module, "upload_pending_records", fake_upload_pending_records)
    service = DesktopDataService()
    result = service.auto_collect_all_devices()

    assert result["uploaded"] == 1
    assert len(upload_calls) == 1
    assert len(upload_calls[0]["task_ids"]) == 1


def test_auto_collect_selected_devices_uploads_pending_tasks_after_collect(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    upload_calls: list[dict] = []

    def fake_upload_pending_records(db, *, task_ids=None, max_tasks=20):
        upload_calls.append({"called": True, "task_ids": list(task_ids or [])})
        return {"success": True, "processed": 1, "uploaded": 1, "failed": 0}

    monkeypatch.setattr(service_module, "upload_pending_records", fake_upload_pending_records)
    service = DesktopDataService()
    result = service.auto_collect_selected_devices([1])

    assert result["uploaded"] == 1
    assert len(upload_calls) == 1
    assert len(upload_calls[0]["task_ids"]) == 1


def test_auto_collect_only_uploads_newly_created_pending_tasks(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)

    created_task_ids: list[int] = []

    def fake_collect_once(db, device):
        db.add(
            UploadTask(
                task_type="telemetry",
                payload_json='{"device_id": 1, "metrics": [{"metric_code": "w01010", "metric_value": 0.0}]}',
                status="pending",
            )
        )
        db.commit()
        created_task_ids.append(db.query(UploadTask).order_by(UploadTask.id.desc()).first().id)
        return FakeCollectResult(device.id, device.device_code, datetime(2026, 7, 1, 12, 0, 0), [FakeMetric("w01010", "水温", 0.0, "℃")])

    captured = {}

    def fake_upload_pending_records(db, *, task_ids=None, max_tasks=20):
        captured["task_ids"] = list(task_ids or [])
        captured["max_tasks"] = max_tasks
        return {"success": True, "processed": len(task_ids or []), "uploaded": len(task_ids or []), "failed": 0}

    monkeypatch.setattr(service_module, "collect_once", fake_collect_once)
    monkeypatch.setattr(service_module, "upload_pending_records", fake_upload_pending_records)
    service = DesktopDataService()
    service.auto_collect_all_devices()

    assert captured["task_ids"] == created_task_ids


def test_auto_collect_skips_upload_when_no_new_pending_tasks(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    monkeypatch.setattr(
        service_module,
        "collect_once",
        lambda db, device: FakeCollectResult(device.id, device.device_code, datetime(2026, 7, 1, 12, 0, 0), [FakeMetric("w01010", "水温", 0.0, "℃")]),
    )
    captured = {"called": False}

    def fake_upload_pending_records(db, *, task_ids=None, max_tasks=20):
        captured["called"] = True
        return {"success": True, "processed": 0, "uploaded": 0, "failed": 0}

    monkeypatch.setattr(service_module, "upload_pending_records", fake_upload_pending_records)
    service = DesktopDataService()
    result = service.auto_collect_all_devices()

    assert captured["called"] is False
    assert result["processed"] == 0


def test_upload_pending_tasks_delegates_to_uploader(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    monkeypatch.setattr(service_module, "upload_pending_records", lambda db: {"success": True, "processed": 3, "uploaded": 2, "failed": 1})
    service = DesktopDataService()
    result = service.upload_pending_tasks()
    assert result["uploaded"] == 2


def test_retry_failed_upload_tasks_delegates_to_resetter(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    monkeypatch.setattr(service_module, "reset_failed_upload_tasks", lambda db: {"success": True, "reset": 1})
    service = DesktopDataService()
    result = service.retry_failed_upload_tasks()
    assert result["reset"] == 1


def test_fetch_upload_tasks_includes_packet_preview_and_result_summary(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    monkeypatch.setattr(
        service_module,
        "fetch_platform_env_settings",
        lambda: {"platform_host": "127.0.0.1", "platform_port": 9000, "site_code": "SITE-001", "gateway_code": "A110000_0001"},
    )

    with session_factory() as db:
        task = db.query(UploadTask).first()
        task.task_type = "telemetry"
        task.status = "pending"
        task.last_error = "连接成功但未收到 ACK（等待 3 秒）"
        task.payload_json = (
            '{"device_id": 1, "device_code": "DEV-001", "collected_at": "2026-07-06T11:14:40", '
            '"metrics": [{"metric_code": "w01010", "metric_name": "水温", "metric_value": 28.5, "metric_unit": "℃"}]}'
        )
        db.commit()

    service = DesktopDataService()
    rows = service.fetch_upload_tasks(limit=1)

    assert rows[0]["device_code"] == "DEV-001"
    assert rows[0]["command_code"] == "2011"
    assert rows[0]["result_text"] == "连接成功但未收到 ACK（等待 3 秒）"
    assert "w01010-Rtd=28.5" in rows[0]["packet_preview"]


def test_fetch_platform_runtime_status_and_last_packet_snapshot(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    monkeypatch.setattr(
        service_module,
        "fetch_platform_env_settings",
        lambda: {"platform_host": "127.0.0.1", "platform_port": 9100, "site_code": "SITE-001", "gateway_code": "A110000_0001"},
    )

    class FakeClient:
        @classmethod
        def get_runtime_status(cls):
            return {
                "connection_status": "connected",
                "last_send_time": "2026-07-06 13:09:10",
                "last_send_result": "ack",
                "ack_received": True,
                "last_response": "##0075QN=20260706103512345;ST=91;CN=9014;PW=123456;MN=A110000_0001;Flag=8;CP=&&&&0140",
                "last_packet": "##0247QN=20260706103512345;ST=21;CN=2011;PW=123456;MN=A110000_0001;Flag=9;CP=&&DataTime=20260706103000;w01010-Rtd=28.6,w01010-Flag=N&&1540\\r\\n",
                "endpoint": "127.0.0.1:9100",
            }

    monkeypatch.setattr(service_module, "RestPlatformClient", FakeClient)
    service = DesktopDataService()

    status = service.fetch_platform_runtime_status()
    packet = service.fetch_last_packet_snapshot()

    assert status.connection_status == "已连接"
    assert status.ack_status == "已收到 ACK"
    assert status.endpoint == "127.0.0.1:9100"
    assert packet.packet_text.startswith("##0247")
    assert packet.ack_policy == "必须"
    assert packet.ack_timeout_seconds == 3.0


def test_export_latest_telemetry_csv_creates_file(monkeypatch, tmp_path: Path):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    file_path = service.export_latest_telemetry_csv(tmp_path, limit=10)
    assert file_path.exists()
    content = file_path.read_text(encoding="utf-8-sig")
    assert "设备名称" in content
    assert "测试设备1" in content


def test_export_query_rows_csv_creates_file(monkeypatch, tmp_path: Path):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    file_path = service.export_query_rows_csv(
        tmp_path,
        [
            {
                "pond_code": "POND-01",
                "device_code": "DEV-001",
                "device_name": "Test Device",
                "metric_code": "water_temp",
                "metric_name": "Water Temp",
                "metric_value": 28.5,
                "metric_unit": "C",
                "quality": "good",
                "collected_at": "2026-07-02 10:00:00",
            }
        ],
        "realtime",
    )
    assert file_path.exists()
    content = file_path.read_text(encoding="utf-8-sig")
    assert "DEV-001" in content
    assert "Water Temp" in content

def test_save_factor_bindings_uses_catalog_defaults(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    updated = service.save_factor_bindings(
        1,
        [
            {
                "id": "",
                "metric_code": "w21003",
                "lower_limit": "0.1",
                "upper_limit": "2.5",
            }
        ],
    )
    assert updated[0]["metric_code"] == "w21003"
    assert updated[0]["metric_name"] == "氨氮"
    assert updated[0]["metric_unit"] == "mg/L"


def test_delete_serial_profile_rejects_bound_rtu_profile(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    service.save_acquisition_profile(
        "RTU模板-绑定串口",
        "modbus_rtu",
        "serial",
        "默认串口1",
        5,
        "float32",
        "30031",
        False,
    )
    try:
        service.delete_serial_profile("默认串口1")
    except ValueError as exc:
        assert "Modbus RTU" in str(exc)
    else:
        raise AssertionError("expected bound serial profile deletion to be rejected")

def test_fetch_devices_includes_config_status(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    devices = service.fetch_devices()
    row = next(item for item in devices if item["device_code"] == "DEV-001")
    assert row["config_status"] == "已完成"
    assert "未绑定监测因子" not in row["config_hint"]


def test_test_device_connection_includes_config_hint(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    service.update_device(
        1,
        {
            "site_id": 1,
            "pond_code": "POND-01",
            "device_name": "测试设备1",
            "device_type": "water_quality",
            "protocol_type": "modbus_tcp",
            "connection_type": "tcp",
            "sort_order": 1,
            "config_json": '{"host": "192.168.1.50"}',
        },
    )
    result = service.test_device_connection(1)
    assert result.success is False
    assert any("配置完整度" in line for line in result.details)
    assert any("待完善项" in line for line in result.details)

def test_save_platform_settings_rejects_missing_gateway(monkeypatch):
    def fake_save(_host, _port, _site, gateway):
        if not gateway.strip():
            raise ValueError("网关编码不能为空")
        return {"platform_host": _host, "platform_port": _port, "site_code": _site, "gateway_code": gateway}

    monkeypatch.setattr(service_module, "fetch_platform_env_settings", lambda: {"platform_host": "192.168.1.9", "platform_port": 9001, "site_code": "SITE-9", "gateway_code": "GW-9"})
    monkeypatch.setattr(service_module, "save_platform_env_settings", fake_save)
    service = DesktopDataService()
    try:
        service.save_platform_settings("10.0.0.8", 7000, "S1", "")
    except ValueError as exc:
        assert "网关编码不能为空" in str(exc)
    else:
        raise AssertionError("expected missing gateway code to be rejected")

def test_trigger_collect_rejects_incomplete_config(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    service.update_device(
        1,
        {
            "site_id": 1,
            "pond_code": "POND-01",
            "device_name": "测试设备1",
            "device_type": "water_quality",
            "protocol_type": "modbus_tcp",
            "connection_type": "tcp",
            "sort_order": 1,
            "config_json": '{"host": "192.168.1.50"}',
        },
    )
    try:
        service.trigger_collect(1)
    except ValueError as exc:
        assert "配置未完成" in str(exc)
    else:
        raise AssertionError("expected incomplete device config to block collect")

def test_auto_collect_skips_incomplete_devices(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    monkeypatch.setattr(service_module, "collect_once", lambda db, device: FakeCollectResult(device.id, device.device_code, datetime(2026, 7, 1, 12, 0, 0), [FakeMetric("water_temp", "水温", 28.5, "C")]))
    service = DesktopDataService()
    service.update_device(
        2,
        {
            "site_id": 1,
            "pond_code": "POND-02",
            "device_name": "测试设备2",
            "device_type": "water_quality",
            "protocol_type": "modbus_tcp",
            "connection_type": "tcp",
            "sort_order": 2,
            "config_json": '{"host": "192.168.1.60"}',
        },
    )
    result = service.auto_collect_all_devices()
    assert result["device_count"] >= 1
    assert result["skipped_count"] >= 1


def test_fetch_analysis_summary_uses_configurable_thresholds(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    with session_factory() as db:
        db.add(
            TelemetryRecord(
                device_id=1,
                metric_code="w01014",
                metric_name="溶解氧",
                metric_value=2.5,
                metric_unit="mg/L",
                quality="warning",
                collected_at=datetime(2026, 7, 6, 10, 0, 0),
            )
        )
        db.add(
            TelemetryRecord(
                device_id=1,
                metric_code="w01001",
                metric_name="pH",
                metric_value=8.2,
                metric_unit="无量纲",
                quality="good",
                collected_at=datetime(2026, 7, 6, 10, 1, 0),
            )
        )
        db.add(
            SystemSetting(
                setting_key="analysis_thresholds_json",
                setting_value='{"w01014": {"lower": 3.0, "upper": null, "advice": "溶氧偏低，建议增氧。"}}',
                setting_name="数据分析阈值",
                setting_group="analysis",
            )
        )
        db.commit()

    service = DesktopDataService()
    summary = service.fetch_analysis_summary(window_hours=72)
    current = {row.metric_code: row for row in summary.metrics}
    assert "w01014" in current
    assert current["w01014"].status == "warning"
    assert "建议增氧" in current["w01014"].advice
    assert "超标" in current["w01014"].quality_tip
    assert summary.thresholds["w01014"].lower == 3.0


def test_analysis_defaults_use_project_surface_water_requirements(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    service = DesktopDataService()
    summary = service.fetch_analysis_summary(window_hours=72)
    sources = " ".join(threshold.source for threshold in summary.thresholds.values())
    metric_codes = {row.metric_code for row in summary.metrics}

    assert "本项目地表水技术要求目录" in sources
    assert "GB 11607" not in sources
    assert {"w01010", "w01001", "w01014", "w01019", "w01003"}.issubset(metric_codes)
    assert {"w01018", "w21003", "w21011", "w21001"}.issubset(metric_codes)


def test_fetch_analysis_summary_flags_outlier_and_constant_values(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    with session_factory() as db:
        for index, value in enumerate([7.8, 7.8, 7.8, 7.8, 7.8]):
            db.add(
                TelemetryRecord(
                    device_id=1,
                    metric_code="w01001",
                    metric_name="pH",
                    metric_value=value,
                    metric_unit="无量纲",
                    quality="good",
                    collected_at=datetime(2026, 7, 6, 9, index, 0),
                )
            )
        for index, value in enumerate([25.0, 25.1, 25.0, 25.2, 40.0]):
            db.add(
                TelemetryRecord(
                    device_id=1,
                    metric_code="w01010",
                    metric_name="水温",
                    metric_value=value,
                    metric_unit="℃",
                    quality="warning" if value > 32 else "good",
                    collected_at=datetime(2026, 7, 6, 9, index, 0),
                )
            )
        db.commit()

    service = DesktopDataService()
    summary = service.fetch_analysis_summary(window_hours=72)
    current = {row.metric_code: row for row in summary.metrics}
    assert "疑似恒值" in current["w01001"].quality_tip
    assert "疑似离群" in current["w01010"].quality_tip


def test_fetch_upload_queue_status_distinguishes_retry_and_skipped(monkeypatch):
    session_factory = build_test_session_factory()
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    with session_factory() as db:
        db.add(UploadTask(task_type="telemetry", payload_json='{"device_id": 1}', status="pending", retry_count=0))
        db.add(UploadTask(task_type="telemetry", payload_json='{"device_id": 1}', status="failed", retry_count=5))
        db.add(UploadTask(task_type="telemetry", payload_json='{"device_id": 1}', status="skipped", retry_count=0))
        db.commit()

    service = DesktopDataService()
    status = service.fetch_upload_queue_status()
    assert status.pending_count >= 1
    assert status.failed_count >= 1
    assert status.skipped_count == 1
    assert "补传" in status.summary_text
