import json
import hashlib
import threading
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.upload_task import UploadTask
from app.services.factor_normalizer import normalize_metric_payload
from app.services.platform.rest_client import RestPlatformClient


MAX_UPLOAD_RETRY_COUNT = 5
_shared_platform_client: RestPlatformClient | None = None
_upload_lock = threading.Lock()


def _get_platform_client() -> RestPlatformClient:
    global _shared_platform_client
    if _shared_platform_client is None:
        _shared_platform_client = RestPlatformClient()
    return _shared_platform_client


def _resolve_command_code(task_type: str) -> str:
    if task_type == "telemetry":
        return "2011"
    if task_type == "hourly":
        return "2061"
    raise ValueError(f"unsupported upload task type: {task_type}")


def _metric_data_flag(metric: dict) -> str:
    quality = str(metric.get("quality") or metric.get("analysis_status") or metric.get("flag") or "").strip().lower()
    if quality and quality not in {"good", "normal", "n"}:
        return "D"
    return "N"


def _payload_fingerprint(payload: dict, command_code: str) -> str:
    data_time = payload.get("collected_at") or payload.get("hour_bucket") or ""
    metrics = []
    for item in payload.get("metrics", []):
        metrics.append(
            {
                "code": str(item.get("metric_code", "")),
                "value": item.get("metric_value"),
                "data_flag": _metric_data_flag(item),
            }
        )
    metrics.sort(key=lambda item: (item["code"], str(item["value"]), str(item["data_flag"])))
    source = {
        "mn": settings.gateway_code.strip(),
        "cn": command_code,
        "packet_flag": "9",
        "data_time": str(data_time),
        "metrics": metrics,
    }
    raw = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def upload_pending_records(db: Session, *, max_tasks: int = 20, task_ids: list[int] | None = None) -> dict:
    if not _upload_lock.acquire(blocking=False):
        return {
            "success": True,
            "processed": 0,
            "uploaded": 0,
            "failed": 0,
            "skipped": 0,
            "message": "上传任务正在执行，已跳过本次重复触发",
        }
    try:
        return _upload_pending_records_locked(db, max_tasks=max_tasks, task_ids=task_ids)
    finally:
        _upload_lock.release()


def _upload_pending_records_locked(db: Session, *, max_tasks: int = 20, task_ids: list[int] | None = None) -> dict:
    client = _get_platform_client()
    query = db.query(UploadTask).filter(UploadTask.status == "pending")
    if task_ids:
        query = query.filter(UploadTask.id.in_(task_ids))
    tasks = query.order_by(UploadTask.id.asc()).limit(max_tasks).all()

    success_count = 0
    failed_count = 0
    skipped_count = 0
    attempted_fingerprints: dict[str, bool] = {}

    for task in tasks:
        payload = normalize_metric_payload(json.loads(task.payload_json))
        task.payload_json = json.dumps(payload, ensure_ascii=False)
        command_code = _resolve_command_code(task.task_type)
        fingerprint = _payload_fingerprint(payload, command_code)
        if fingerprint in attempted_fingerprints:
            if attempted_fingerprints[fingerprint]:
                task.status = "skipped"
                task.last_error = f"重复报文已跳过：{fingerprint[:12]}"
                task.updated_at = datetime.now()
                skipped_count += 1
            else:
                task.last_error = f"同批重复报文已暂缓，等待下一轮重试：{fingerprint[:12]}"
                task.updated_at = datetime.now()
                skipped_count += 1
            continue

        result = client.upload_payload(payload, command_code=command_code)
        if result.get("success"):
            task.status = "uploaded"
            task.last_error = str(result.get("response") or "SENT")
            task.updated_at = datetime.now()
            success_count += 1
            attempted_fingerprints[fingerprint] = True
        else:
            task.retry_count += 1
            task.last_error = result.get("error")
            task.status = "failed" if task.retry_count >= MAX_UPLOAD_RETRY_COUNT else "pending"
            task.updated_at = datetime.now()
            failed_count += 1
            attempted_fingerprints[fingerprint] = False
    db.commit()

    return {
        "success": True,
        "processed": len(tasks),
        "uploaded": success_count,
        "failed": failed_count,
        "skipped": skipped_count,
    }


def reset_failed_upload_tasks(db: Session, limit: int = 100) -> dict:
    tasks = (
        db.query(UploadTask)
        .filter(UploadTask.status == "failed")
        .order_by(UploadTask.updated_at.desc(), UploadTask.id.desc())
        .limit(limit)
        .all()
    )
    for task in tasks:
        task.status = "pending"
        task.last_error = None
        task.updated_at = datetime.now()
    db.commit()
    return {"success": True, "reset": len(tasks)}
