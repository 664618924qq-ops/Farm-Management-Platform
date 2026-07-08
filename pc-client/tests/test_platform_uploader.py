from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.upload_task import UploadTask
from app.services import platform_uploader as uploader_module


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_upload_pending_records_marks_failed_after_max_retry(monkeypatch):
    uploader_module._shared_platform_client = None
    maker = build_session()
    with maker() as db:
        db.add(
            UploadTask(
                task_type="telemetry",
                payload_json='{"device_id": 1}',
                status="pending",
                retry_count=4,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        db.commit()

    class FakeClient:
        def upload_payload(self, payload: dict, *, command_code: str) -> dict:
            assert command_code == "2011"
            return {"success": False, "error": "timeout"}

    monkeypatch.setattr(uploader_module, "RestPlatformClient", lambda: FakeClient())

    with maker() as db:
        result = uploader_module.upload_pending_records(db)
        task = db.query(UploadTask).first()

    assert result["failed"] == 1
    assert task.status == "failed"
    assert task.retry_count == 5


def test_reset_failed_upload_tasks_moves_tasks_back_to_pending():
    uploader_module._shared_platform_client = None
    maker = build_session()
    with maker() as db:
        db.add(
            UploadTask(
                task_type="telemetry",
                payload_json='{"device_id": 1}',
                status="failed",
                retry_count=5,
                last_error="timeout",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        db.commit()

    with maker() as db:
        result = uploader_module.reset_failed_upload_tasks(db)
        task = db.query(UploadTask).first()

    assert result["reset"] == 1
    assert task.status == "pending"
    assert task.last_error is None


def test_upload_pending_records_uses_2061_for_hourly_tasks(monkeypatch):
    uploader_module._shared_platform_client = None
    maker = build_session()
    with maker() as db:
        db.add(
            UploadTask(
                task_type="hourly",
                payload_json='{"device_id": 1, "hour_bucket": "2026-07-06T10:00:00", "collected_at": "2026-07-06T10:00:00", "metrics": [{"metric_code": "w01010", "metric_value": 28.4}]}',
                status="pending",
                retry_count=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        db.commit()

    class FakeClient:
        def upload_payload(self, payload: dict, *, command_code: str) -> dict:
            assert command_code == "2061"
            assert payload["hour_bucket"] == "2026-07-06T10:00:00"
            return {"success": True, "response": "ACK"}

    monkeypatch.setattr(uploader_module, "RestPlatformClient", lambda: FakeClient())

    with maker() as db:
        result = uploader_module.upload_pending_records(db)
        task = db.query(UploadTask).filter(UploadTask.task_type == "hourly").first()

    assert result["uploaded"] == 1
    assert task.status == "uploaded"


def test_upload_pending_records_normalizes_legacy_factor_codes(monkeypatch):
    uploader_module._shared_platform_client = None
    maker = build_session()
    with maker() as db:
        db.add(
            UploadTask(
                task_type="telemetry",
                payload_json='{"device_id": 2, "device_code": "DEV-002", "collected_at": "2026-07-06T11:14:40", "metrics": [{"metric_code": "water_temp", "metric_name": "水温", "metric_value": 0.0, "metric_unit": "C"}, {"metric_code": "ph", "metric_name": "pH", "metric_value": 0.0, "metric_unit": null}, {"metric_code": "do", "metric_name": "溶解氧", "metric_value": 0.0, "metric_unit": "mg/L"}]}',
                status="pending",
                retry_count=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        db.commit()

    class FakeClient:
        def upload_payload(self, payload: dict, *, command_code: str) -> dict:
            assert command_code == "2011"
            codes = [item["metric_code"] for item in payload["metrics"]]
            assert codes == ["w01010", "w01001", "w01014"]
            return {"success": True, "response": "ACK"}

    monkeypatch.setattr(uploader_module, "RestPlatformClient", lambda: FakeClient())

    with maker() as db:
        result = uploader_module.upload_pending_records(db, max_tasks=1)
        task = db.query(UploadTask).first()

    assert result["uploaded"] == 1
    assert '"w01010"' in task.payload_json


def test_upload_pending_records_reuses_single_platform_client_instance(monkeypatch):
    uploader_module._shared_platform_client = None
    maker = build_session()
    with maker() as db:
        db.add(
            UploadTask(
                task_type="telemetry",
                payload_json='{"device_id": 1, "collected_at": "2026-07-06T11:14:40", "metrics": [{"metric_code": "w01010", "metric_name": "水温", "metric_value": 0.0, "metric_unit": "℃"}]}',
                status="pending",
                retry_count=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        db.commit()

    created_clients = []

    class FakeClient:
        def __init__(self):
            self.calls = 0
            self.closed = False
            created_clients.append(self)

        def upload_payload(self, payload: dict, *, command_code: str) -> dict:
            self.calls += 1
            return {"success": True, "response": "ACK"}

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(uploader_module, "RestPlatformClient", FakeClient)
    uploader_module._shared_platform_client = None

    with maker() as db:
        result = uploader_module.upload_pending_records(db, max_tasks=1)

    assert result["uploaded"] == 1
    assert len(created_clients) == 1
    assert created_clients[0].calls == 1
    assert created_clients[0].closed is False


def test_upload_pending_records_keeps_pending_when_9014_ack_missing(monkeypatch):
    uploader_module._shared_platform_client = None
    maker = build_session()
    with maker() as db:
        db.add(
            UploadTask(
                task_type="telemetry",
                payload_json='{"device_id": 1, "device_code": "DEV-001", "collected_at": "2026-07-06T11:14:40", "metrics": [{"metric_code": "w01010", "metric_name": "姘存俯", "metric_value": 0.0, "metric_unit": "鈩?"}]}',
                status="pending",
                retry_count=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        db.commit()

    class FakeClient:
        def upload_payload(self, payload: dict, *, command_code: str) -> dict:
            return {"success": False, "error": "连接成功但未收到 ACK（等待 3 秒）"}

    monkeypatch.setattr(uploader_module, "RestPlatformClient", lambda: FakeClient())

    with maker() as db:
        result = uploader_module.upload_pending_records(db, max_tasks=1)
        task = db.query(UploadTask).first()

    assert result["failed"] == 1
    assert task.status == "pending"
    assert task.last_error == "连接成功但未收到 ACK（等待 3 秒）"


def test_upload_pending_records_skips_duplicate_payloads_in_one_batch(monkeypatch):
    uploader_module._shared_platform_client = None
    maker = build_session()
    duplicate_payload = (
        '{"device_id": 1, "device_code": "DEV-001", "collected_at": "2026-07-06T11:14:40", '
        '"metrics": [{"metric_code": "w01010", "metric_name": "水温", "metric_value": 28.5, "metric_unit": "℃"}]}'
    )
    with maker() as db:
        db.add(
            UploadTask(
                task_type="telemetry",
                payload_json=duplicate_payload,
                status="pending",
                retry_count=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        db.add(
            UploadTask(
                task_type="telemetry",
                payload_json=duplicate_payload,
                status="pending",
                retry_count=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        db.commit()

    calls = []

    class FakeClient:
        def upload_payload(self, payload: dict, *, command_code: str) -> dict:
            calls.append((payload, command_code))
            return {"success": True, "response": "ACK"}

    monkeypatch.setattr(uploader_module, "RestPlatformClient", lambda: FakeClient())

    with maker() as db:
        result = uploader_module.upload_pending_records(db, max_tasks=10)
        tasks = db.query(UploadTask).order_by(UploadTask.id.asc()).all()

    assert result["processed"] == 2
    assert result["uploaded"] == 1
    assert result["skipped"] == 1
    assert len(calls) == 1
    assert tasks[0].status == "uploaded"
    assert tasks[1].status == "skipped"
    assert "重复报文已跳过" in tasks[1].last_error
