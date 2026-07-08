from __future__ import annotations

import csv
import inspect
import json
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, or_, text as sql_text

from app.core.config import fetch_platform_env_settings, save_platform_env_settings, settings
from app.db.session import SessionLocal
from app.models.alert import AlertEvent
from app.models.device import Device
from app.models.metric import DeviceMetric
from app.models.site import Site
from app.models.system_setting import SystemSetting
from app.models.telemetry import TelemetryRecord
from app.models.upload_task import UploadTask
from app.services.collector import ALLOWED_SAVE_INTERVAL_SECONDS, collect_once
from app.services.factor_normalizer import normalize_metric_fields, normalize_metric_payload
from app.services.platform.hj212 import build_hourly_packet, build_realtime_packet
from app.services.platform.rest_client import RestPlatformClient
from app.services.platform_uploader import reset_failed_upload_tasks, upload_pending_records


@dataclass
class OverviewStats:
    site_count: int
    device_count: int
    online_device_count: int
    alert_count: int
    pending_upload_count: int


@dataclass
class RuntimeSettings:
    auto_save_enabled: bool
    save_interval_seconds: int


@dataclass
class PlatformSettings:
    platform_host: str
    platform_port: int
    site_code: str
    gateway_code: str


@dataclass
class PlatformRuntimeStatus:
    connection_status: str
    last_send_time: str
    last_send_result: str
    ack_status: str
    last_response: str
    endpoint: str


@dataclass
class LastPacketSnapshot:
    packet_text: str
    endpoint: str
    ack_policy: str
    gateway_code: str
    ack_timeout_seconds: float


@dataclass
class AcquisitionSettings:
    default_protocol: str
    default_connection: str
    default_config_template: str
    collect_timeout_seconds: int


@dataclass
class AcquisitionProfile:
    profile_name: str
    protocol_type: str
    connection_type: str
    serial_profile_name: str
    collect_timeout_seconds: int
    data_type: str
    register_address: str
    is_default: bool


@dataclass
class SerialProfile:
    profile_name: str
    port_name: str
    baudrate: int
    data_bits: int
    parity: str
    stop_bits: int
    slave_address: int
    is_default: bool


@dataclass
class SerialSettings:
    port_name: str
    baudrate: int
    data_bits: int
    parity: str
    stop_bits: int
    slave_address: int


@dataclass
class ConnectionTestResult:
    success: bool
    status: str
    message: str
    details: list[str]


@dataclass
class UploadQueueStatus:
    pending_count: int
    failed_count: int
    skipped_count: int
    uploaded_count: int
    summary_text: str


@dataclass
class AnalysisThreshold:
    lower: float | None
    upper: float | None
    advice: str
    source: str


@dataclass
class MetricAnalysis:
    metric_code: str
    metric_name: str
    metric_unit: str
    latest_value: float | None
    min_value: float | None
    max_value: float | None
    avg_value: float | None
    sample_count: int
    trend: str
    status: str
    advice: str
    quality_tip: str
    latest_time: str
    sparkline: str


@dataclass
class AnalysisSummary:
    generated_at: str
    window_hours: int
    metrics: list[MetricAnalysis]
    thresholds: dict[str, AnalysisThreshold]


DEFAULT_WATER_FACTORS = [
    {"code": "w01010", "name": "水温", "unit": "℃"},
    {"code": "w01001", "name": "pH", "unit": "无量纲"},
    {"code": "w01014", "name": "溶解氧", "unit": "mg/L"},
    {"code": "w01003", "name": "浊度", "unit": "NTU"},
    {"code": "w01019", "name": "电导率", "unit": "uS/cm"},
    {"code": "w01017", "name": "盐度", "unit": "‰"},
    {"code": "w01013", "name": "ORP", "unit": "mV"},
    {"code": "w21003", "name": "氨氮", "unit": "mg/L"},
    {"code": "w21011", "name": "总磷", "unit": "mg/L"},
    {"code": "w21001", "name": "总氮", "unit": "mg/L"},
    {"code": "w01018", "name": "高锰酸盐指数", "unit": "mg/L"},
    {"code": "w01022", "name": "蓝绿藻", "unit": "mg/L"},
    {"code": "w01016", "name": "叶绿素a", "unit": "ug/L"},
]

DEFAULT_ANALYSIS_THRESHOLDS: dict[str, AnalysisThreshold] = {
    "w01010": AnalysisThreshold(None, None, "水温为本项目地表水技术要求关注项，建议结合日变化趋势、现场天气和探头校准记录复核。", "来源：本项目地表水技术要求目录 + analysis_thresholds_json 可配置阈值；水温以趋势复核为主。"),
    "w01001": AnalysisThreshold(6.0, 9.0, "pH 超出参考范围时，建议复核现场采样、探头校准和上下游来水变化。", "来源：本项目地表水技术要求目录 + analysis_thresholds_json 可配置阈值；默认参考地表水常用 pH 范围 6-9。"),
    "w01014": AnalysisThreshold(3.0, None, "溶解氧低于参考下限时，建议复核现场水体交换、耗氧负荷和仪表状态。", "来源：本项目地表水技术要求目录 + analysis_thresholds_json 可配置阈值；默认参考地表水 IV 类溶解氧下限 3 mg/L。"),
    "w01019": AnalysisThreshold(None, None, "电导率用于辅助判断水体离子变化，建议结合历史趋势、降雨和来水来源复核。", "来源：本项目地表水技术要求目录 + analysis_thresholds_json 可配置阈值；电导率作为趋势辅助项。"),
    "w01003": AnalysisThreshold(None, None, "浊度用于辅助判断悬浮物或扰动变化，建议结合现场水色、降雨和采样点变化复核。", "来源：本项目地表水技术要求目录 + analysis_thresholds_json 可配置阈值；浊度作为趋势辅助项。"),
    "w01018": AnalysisThreshold(None, 10.0, "高锰酸盐指数偏高时，建议复核有机污染来源、采样时段和平台侧分类阈值。", "来源：本项目地表水技术要求目录 + analysis_thresholds_json 可配置阈值；默认参考地表水 IV 类限值 10 mg/L。"),
    "w21003": AnalysisThreshold(None, 1.5, "氨氮偏高时，建议复核来水、排口影响和实验/传感器校准结果。", "来源：本项目地表水技术要求目录 + analysis_thresholds_json 可配置阈值；默认参考地表水 IV 类限值 1.5 mg/L。"),
    "w21011": AnalysisThreshold(None, 0.3, "总磷偏高时，建议复核营养盐来源、降雨径流和采样代表性。", "来源：本项目地表水技术要求目录 + analysis_thresholds_json 可配置阈值；默认参考地表水 IV 类湖库外限值 0.3 mg/L。"),
    "w21001": AnalysisThreshold(None, 1.5, "总氮偏高时，建议复核氮源输入、采样位置和平台侧评价类别。", "来源：本项目地表水技术要求目录 + analysis_thresholds_json 可配置阈值；默认参考地表水 IV 类限值 1.5 mg/L。"),
}

DEFAULT_ANALYSIS_QUALITY_RULES = {
    "outlier_min_samples": 5,
    "outlier_delta_ratio": 0.25,
    "constant_min_samples": 5,
    "constant_delta": 0.01,
}


def normalize_save_interval_seconds(value: int | str | None) -> int:
    try:
        interval = int(value) if value is not None else 30
    except (TypeError, ValueError):
        interval = 30
    if interval == 60:
        return 60
    return 30


def _factor_summary_text(metrics: list[DeviceMetric]) -> str:
    names = [str(row.metric_name or row.metric_code).strip() for row in metrics if str(row.metric_name or row.metric_code).strip()]
    if not names:
        return "未绑定因子"
    preview = "、".join(names[:4])
    if len(names) > 4:
        preview += f" 等{len(names)}项"
    return preview


class DesktopDataService:
    _standard_factor_mapping_session_source: int | None = None

    def __init__(self) -> None:
        self._ensure_standard_factor_mappings()

    def _ensure_standard_factor_mappings(self) -> None:
        session_source = id(SessionLocal)
        if self.__class__._standard_factor_mapping_session_source == session_source:
            return
        with SessionLocal() as db:
            self._ensure_large_setting_value_column(db)
            updated = False

            record = db.query(SystemSetting).filter(SystemSetting.setting_key == "factor_catalog_json").first()
            if record is None or not str(record.setting_value).strip():
                payload_json = json.dumps(DEFAULT_WATER_FACTORS, ensure_ascii=False, separators=(",", ":"))
                if record is None:
                    db.add(
                        SystemSetting(
                            setting_key="factor_catalog_json",
                            setting_name="常规水质因子字典",
                            setting_group="factor",
                            description="维护因子配置下拉框中的常规水质因子字典。",
                            setting_value=payload_json,
                        )
                    )
                else:
                    record.setting_value = payload_json
                updated = True

            for row in db.query(DeviceMetric).all():
                normalized_code, normalized_name, normalized_unit = normalize_metric_fields(
                    row.metric_code,
                    row.metric_name,
                    row.metric_unit,
                )
                if (
                    normalized_code != row.metric_code
                    or normalized_name != row.metric_name
                    or (normalized_unit or None) != (row.metric_unit or None)
                ):
                    row.metric_code = normalized_code
                    row.metric_name = normalized_name
                    row.metric_unit = normalized_unit
                    updated = True

            if updated:
                db.commit()
        self.__class__._standard_factor_mapping_session_source = session_source

    def _ensure_large_setting_value_column(self, db) -> None:
        if getattr(self, "_setting_value_column_checked", False):
            return
        bind = db.get_bind()
        dialect_name = bind.dialect.name
        try:
            if dialect_name == "mysql":
                db.execute(sql_text("ALTER TABLE system_settings MODIFY setting_value TEXT NOT NULL"))
                db.commit()
        except Exception:
            db.rollback()
        finally:
            self._setting_value_column_checked = True

    def _default_data_type(self, protocol_type: str) -> str:
        return "float32" if protocol_type in {"modbus_tcp", "modbus_rtu"} else "uint16"

    def _build_default_acquisition_profiles(self, settings: AcquisitionSettings) -> list[AcquisitionProfile]:
        profiles: list[AcquisitionProfile] = []
        for profile_name, protocol_type, connection_type in [
            ("Modbus TCP 模板", "modbus_tcp", "tcp"),
            ("Modbus RTU 模板", "modbus_rtu", "serial"),
        ]:
            is_default = settings.default_protocol == protocol_type
            timeout = settings.collect_timeout_seconds if is_default else 5
            profiles.append(
                AcquisitionProfile(
                    profile_name=profile_name,
                    protocol_type=protocol_type,
                    connection_type=connection_type,
                    serial_profile_name="默认串口1" if protocol_type == "modbus_rtu" else "",
                    collect_timeout_seconds=timeout,
                    data_type=self._default_data_type(protocol_type),
                    register_address="30001" if protocol_type == "modbus_rtu" else "40001",
                    is_default=is_default,
                )
            )
        if not any(profile.is_default for profile in profiles):
            profiles[0].is_default = True
        return profiles

    def _build_default_serial_profiles(self, settings: SerialSettings) -> list[SerialProfile]:
        return [
            SerialProfile(
                profile_name="默认串口1",
                port_name=settings.port_name,
                baudrate=settings.baudrate,
                data_bits=settings.data_bits,
                parity=settings.parity,
                stop_bits=settings.stop_bits,
                slave_address=settings.slave_address,
                is_default=True,
            )
        ]

    def _freshness_threshold_seconds(self) -> int:
        settings = self.fetch_runtime_settings()
        return max(settings.save_interval_seconds * 2, 120)

    def _freshness_threshold_seconds_from_db(self, db) -> int:
        settings = {
            row.setting_key: row.setting_value
            for row in db.query(SystemSetting)
            .filter(SystemSetting.setting_key.in_(["save_interval_seconds"]))
            .all()
        }
        return max(normalize_save_interval_seconds(settings.get("save_interval_seconds", "30")) * 2, 120)

    def _resolve_device_status(self, last_collected_at: datetime | None, freshness_threshold_seconds: int | None = None) -> str:
        threshold_seconds = freshness_threshold_seconds or self._freshness_threshold_seconds()
        if last_collected_at is None:
            return "no_data"
        if last_collected_at >= datetime.now() - timedelta(seconds=threshold_seconds):
            return "online"
        return "stale"

    def _device_health_alert_code(self) -> str:
        return "device_health_data_freshness"

    def _normalize_protocol_type(self, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
        if not normalized:
            raise ValueError("协议类型不能为空")
        return normalized

    def _normalize_connection_type(self, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("连接方式不能为空")
        return normalized

    def _parse_optional_float(self, value) -> float | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return float(text)

    def _normalize_register_address(self, value: str, *, field_label: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_label}不能为空")
        if not normalized.isdigit():
            raise ValueError(f"{field_label}必须填写数字寄存器地址")
        return normalized

    def _normalize_device_config(self, raw_config: str) -> str:
        value = raw_config.strip()
        if not value:
            return ""
        try:
            return json.dumps(json.loads(value), ensure_ascii=False)
        except json.JSONDecodeError as exc:
            raise ValueError(f"连接配置 JSON 格式无效: {exc.msg}") from exc

    def _load_device_config(self, device: Device) -> dict:
        if not device.config_json:
            return {}
        try:
            return json.loads(device.config_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"设备 {device.device_code} 的连接配置 JSON 无法解析: {exc.msg}") from exc

    def _device_config_summary(self, device: Device, metrics: list[DeviceMetric] | None = None) -> tuple[str, str]:
        issues: list[str] = []
        config = self._load_device_config(device) if device.config_json else {}
        protocol = (device.protocol_type or "").strip().lower()

        if protocol == "modbus_tcp":
            for field in ["host", "port", "slave"]:
                if config.get(field) in (None, ""):
                    issues.append(f"缺少{field}")
        elif protocol == "modbus_rtu":
            for field in ["serial_port", "baudrate", "slave"]:
                if config.get(field) in (None, ""):
                    issues.append(f"缺少{field}")
        elif protocol == "custom" and not config:
            issues.append("未填写自定义连接参数")

        metric_rows = metrics if metrics is not None else []
        if not metric_rows:
            issues.append("未绑定监测因子")
        if issues:
            return "待完善", "；".join(issues)
        return "已完成", "配置完整"

    def _latest_collected_map(self, db) -> dict[int, datetime]:
        return {
            device_id: collected_at
            for device_id, collected_at in (
                db.query(TelemetryRecord.device_id, func.max(TelemetryRecord.collected_at))
                .group_by(TelemetryRecord.device_id)
                .all()
            )
        }

    def _parse_query_datetime(self, value: str | None, end_of_day: bool = False) -> datetime | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        date = datetime.strptime(text, "%Y-%m-%d")
        if end_of_day:
            return date + timedelta(days=1) - timedelta(seconds=1)
        return date

    def _bucket_time_text(self, source: datetime, granularity: str) -> str:
        if granularity == "minute":
            return source.replace(second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
        if granularity == "hour":
            return source.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:00")
        return source.strftime("%Y-%m-%d %H:%M:%S")

    def _format_upload_time_text(self, value: str | None) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        try:
            return datetime.fromisoformat(text).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return text

    def _build_upload_packet_preview(self, task_type: str, payload: dict, gateway_code: str) -> str:
        if not gateway_code.strip():
            return ""
        normalized_payload = normalize_metric_payload(payload)
        try:
            if task_type == "telemetry":
                return build_realtime_packet(normalized_payload, mn=gateway_code).packet.strip()
            if task_type == "hourly":
                return build_hourly_packet(normalized_payload, mn=gateway_code).packet.strip()
        except Exception:
            return ""
        return ""

    def _upload_result_text(self, row: UploadTask) -> str:
        if row.last_error:
            return row.last_error
        if row.status == "pending":
            return "待发送"
        if row.status == "uploaded":
            return "SENT"
        if row.status == "skipped":
            return "重复报文已跳过"
        return ""

    def _format_connection_status(self, status: str) -> str:
        mapping = {
            "connected": "已连接",
            "disconnected": "未连接",
            "failed": "发送失败",
        }
        return mapping.get(status, status or "未连接")

    def _format_send_result(self, value: str, last_error: str) -> str:
        if value == "ack":
            return "已发送并收到 ACK"
        if value == "sent":
            return "已发送"
        if value == "failed":
            return f"发送失败：{last_error}" if last_error else "发送失败"
        return "尚未发送"

    def _format_ack_status(self, ack_received: bool | None) -> str:
        if ack_received is True:
            return "已收到 ACK"
        if ack_received is False:
            return "未收到 ACK"
        return "尚未判定"

    def fetch_platform_runtime_status(self) -> PlatformRuntimeStatus:
        runtime = RestPlatformClient.get_runtime_status()
        platform_settings = self.fetch_platform_settings()
        endpoint = runtime.get("endpoint") or f"{platform_settings.platform_host}:{platform_settings.platform_port}"
        return PlatformRuntimeStatus(
            connection_status=self._format_connection_status(str(runtime.get("connection_status") or "")),
            last_send_time=str(runtime.get("last_send_time") or ""),
            last_send_result=self._format_send_result(str(runtime.get("last_send_result") or ""), str(runtime.get("last_error") or "")),
            ack_status=self._format_ack_status(runtime.get("ack_received")),
            last_response=str(runtime.get("last_response") or runtime.get("last_error") or ""),
            endpoint=endpoint,
        )

    def fetch_last_packet_snapshot(self) -> LastPacketSnapshot:
        runtime = RestPlatformClient.get_runtime_status()
        platform_settings = self.fetch_platform_settings()
        endpoint = runtime.get("endpoint") or f"{platform_settings.platform_host}:{platform_settings.platform_port}"
        packet_text = str(runtime.get("last_packet") or "")
        if not packet_text:
            with SessionLocal() as db:
                row = db.query(UploadTask).order_by(UploadTask.updated_at.desc(), UploadTask.id.desc()).first()
                if row is not None:
                    try:
                        payload = json.loads(row.payload_json)
                    except json.JSONDecodeError:
                        payload = {}
                    packet_text = self._build_upload_packet_preview(row.task_type, payload, platform_settings.gateway_code)
        return LastPacketSnapshot(
            packet_text=packet_text,
            endpoint=endpoint,
            ack_policy="必须",
            gateway_code=platform_settings.gateway_code,
            ack_timeout_seconds=float(settings.platform_ack_timeout_seconds),
        )

    def acknowledge_alert(self, alert_id: int) -> dict:
        with SessionLocal() as db:
            alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
            if alert is None:
                raise ValueError("alert not found")
            if alert.status == "recovered":
                return {"id": alert.id, "status": alert.status}
            alert.status = "acknowledged"
            db.commit()
            return {"id": alert.id, "status": alert.status}

    def sync_device_health_alerts(self) -> dict:
        with SessionLocal() as db:
            freshness_threshold_seconds = self._freshness_threshold_seconds_from_db(db)
            latest_map = self._latest_collected_map(db)
            devices = db.query(Device).order_by(Device.id.asc()).all()
            active_alerts = {
                row.device_id: row
                for row in db.query(AlertEvent)
                .filter(
                    AlertEvent.alert_code == self._device_health_alert_code(),
                    AlertEvent.status.in_(["active", "acknowledged"]),
                )
                .all()
            }

            created_count = 0
            recovered_count = 0
            for device in devices:
                last_collected_at = latest_map.get(device.id)
                status = self._resolve_device_status(last_collected_at, freshness_threshold_seconds)
                active_alert = active_alerts.get(device.id)
                if status == "online":
                    if active_alert is not None:
                        active_alert.status = "recovered"
                        active_alert.recovered_at = datetime.now()
                        active_alert.alert_message = f"{device.device_name} 数据采集已恢复正常。"
                        recovered_count += 1
                    continue

                if status == "no_data":
                    message = f"{device.device_name} 尚未产生监测数据，请检查设备接线或采集任务。"
                else:
                    last_text = last_collected_at.strftime("%Y-%m-%d %H:%M:%S") if last_collected_at else "未知"
                    message = f"{device.device_name} 数据已过期，最近采集时间 {last_text}。"

                if active_alert is None:
                    db.add(
                        AlertEvent(
                            device_id=device.id,
                            alert_code=self._device_health_alert_code(),
                            alert_level="warning",
                            alert_message=message,
                            status="active",
                        )
                    )
                    created_count += 1
                else:
                    active_alert.alert_message = message
                    active_alert.triggered_at = datetime.now()
            db.commit()
            return {"created": created_count, "recovered": recovered_count}

    def test_device_connection(self, device_id: int) -> ConnectionTestResult:
        with SessionLocal() as db:
            device = db.query(Device).filter(Device.id == device_id).first()
            if device is None:
                raise ValueError("device not found")

            protocol = (device.protocol_type or "").strip().lower()
            config = self._load_device_config(device)
            metrics = (
                db.query(DeviceMetric)
                .filter(DeviceMetric.device_id == device_id)
                .order_by(DeviceMetric.sort_order.asc(), DeviceMetric.id.asc())
                .all()
            )
            config_status, config_hint = self._device_config_summary(device, metrics)
            details = [
                f"设备编号：{device.device_code}",
                f"设备型号：{device.device_type}",
                f"协议类型：{device.protocol_type}",
                f"连接方式：{device.connection_type}",
                f"配置完整度：{config_status}",
            ]
            if config_status != "已完成":
                details.append(f"待完善项：{config_hint}")

            if protocol == "mock":
                details.append("模拟设备已通过连接测试，可直接用于功能演示。")
                return ConnectionTestResult(True, "ready", "模拟设备连接正常。", details)

            if protocol == "modbus_tcp":
                required_fields = ["host", "port", "slave"]
                missing = [field for field in required_fields if config.get(field) in (None, "")]
                if missing:
                    details.append("缺少字段：" + ", ".join(missing))
                    return ConnectionTestResult(False, "config_error", "Modbus TCP 配置不完整。", details)
                details.append(f"目标地址：{config['host']}:{config['port']}")
                details.append(f"从站地址：{config['slave']}")
                return ConnectionTestResult(True, "ready", "Modbus TCP 参数完整，可进入实机联调。", details)

            if protocol == "modbus_rtu":
                serial_port = config.get("serial_port") or config.get("port")
                slave = config.get("slave")
                baudrate = config.get("baudrate")
                missing = []
                if not serial_port:
                    missing.append("serial_port")
                if not slave:
                    missing.append("slave")
                if not baudrate:
                    missing.append("baudrate")
                if missing:
                    details.append("缺少字段：" + ", ".join(missing))
                    return ConnectionTestResult(False, "config_error", "Modbus RTU 配置不完整。", details)
                details.append(f"串口：{serial_port}")
                details.append(f"波特率：{baudrate}")
                details.append(f"从站地址：{slave}")
                return ConnectionTestResult(True, "ready", "Modbus RTU 参数完整，可进入串口联调。", details)

            if protocol == "custom":
                details.append("当前为自定义设备型号，已预留协议扩展入口。")
                details.append("请在连接配置 JSON 中补充该型号所需参数，并在适配器工厂中接入专用驱动。")
                return ConnectionTestResult(True, "extensible", "自定义型号已保存，可继续集成专用协议。", details)

            details.append("当前协议尚未实现专用驱动，建议先使用 mock / modbus_tcp / modbus_rtu / custom。")
            return ConnectionTestResult(False, "unsupported", "当前协议尚未支持连接测试。", details)

    def test_platform_connection(self) -> ConnectionTestResult:
        settings = self.fetch_platform_settings()
        details = [
            f"平台 IP：{settings.platform_host}",
            f"平台端口：{settings.platform_port}",
            f"站点编码：{settings.site_code}",
            f"网关编码：{settings.gateway_code}",
        ]
        if not settings.platform_host.strip():
            return ConnectionTestResult(False, "config_error", "平台 IP 不能为空。", details)
        if settings.platform_port <= 0:
            return ConnectionTestResult(False, "config_error", "平台端口必须大于 0。", details)

        try:
            with socket.create_connection((settings.platform_host.strip(), settings.platform_port), timeout=5.0):
                pass
            details.append("TCP 连接建立成功。")
            return ConnectionTestResult(True, "reachable", "平台 TCP 连接正常。", details)
        except Exception as exc:
            details.append(f"连接异常：{exc}")
            return ConnectionTestResult(False, "network_error", "平台 TCP 连接失败，请检查 IP、端口或服务状态。", details)

    def fetch_overview(self) -> OverviewStats:
        with SessionLocal() as db:
            freshness_threshold_seconds = self._freshness_threshold_seconds_from_db(db)
            self.sync_device_health_alerts()
            site_count = db.query(func.count(Site.id)).scalar() or 0
            device_count = db.query(func.count(Device.id)).scalar() or 0
            latest_map = self._latest_collected_map(db)
            online_device_count = sum(
                1
                for device in db.query(Device).all()
                if self._resolve_device_status(latest_map.get(device.id), freshness_threshold_seconds) == "online"
            )
            alert_count = db.query(func.count(AlertEvent.id)).filter(AlertEvent.status == "active").scalar() or 0
            pending_upload_count = db.query(func.count(UploadTask.id)).filter(UploadTask.status == "pending").scalar() or 0
            return OverviewStats(site_count, device_count, online_device_count, alert_count, pending_upload_count)

    def fetch_platform_settings(self) -> PlatformSettings:
        values = fetch_platform_env_settings()
        return PlatformSettings(**values)

    def save_platform_settings(self, platform_host: str, platform_port: int, site_code: str, gateway_code: str) -> PlatformSettings:
        normalized_host = platform_host.strip()
        normalized_site_code = site_code.strip()
        normalized_gateway_code = gateway_code.strip()
        if not normalized_host:
            raise ValueError("平台 IP 不能为空")
        if int(platform_port) <= 0:
            raise ValueError("平台端口必须大于 0")
        if not normalized_site_code:
            raise ValueError("站点编码不能为空")
        if not normalized_gateway_code:
            raise ValueError("网关编码不能为空")
        values = save_platform_env_settings(normalized_host, int(platform_port), normalized_site_code, normalized_gateway_code)
        return PlatformSettings(**values)

    def fetch_sites(self) -> list[dict]:
        with SessionLocal() as db:
            return [
                {
                    "id": site.id,
                    "site_code": site.site_code,
                    "site_name": site.site_name,
                    "contact_name": site.contact_name or "",
                    "contact_phone": site.contact_phone or "",
                }
                for site in db.query(Site).order_by(Site.id.asc()).all()
            ]

    def fetch_factor_catalog(self) -> list[dict]:
        with SessionLocal() as db:
            self._ensure_large_setting_value_column(db)
            record = db.query(SystemSetting).filter(SystemSetting.setting_key == "factor_catalog_json").first()
            if record is None or not str(record.setting_value).strip():
                return [dict(item) for item in DEFAULT_WATER_FACTORS]
            payload = json.loads(record.setting_value)
            return [
                {
                    "code": str(item.get("code", "")).strip(),
                    "name": str(item.get("name", "")).strip(),
                    "unit": str(item.get("unit", "")).strip(),
                }
                for item in payload
                if str(item.get("code", "")).strip() and str(item.get("name", "")).strip()
            ]

    def save_factor_catalog(self, payload: list[dict]) -> list[dict]:
        cleaned: list[dict] = []
        seen_codes: set[str] = set()
        for item in payload:
            code = str(item.get("code", "")).strip()
            name = str(item.get("name", "")).strip()
            unit = str(item.get("unit", "")).strip()
            if not code:
                raise ValueError("因子编码不能为空")
            if not name:
                raise ValueError("因子名称不能为空")
            if code in seen_codes:
                raise ValueError("因子编码不能重复")
            seen_codes.add(code)
            cleaned.append({"code": code, "name": name, "unit": unit})
        if not cleaned:
            raise ValueError("至少保留一个常规因子")
        with SessionLocal() as db:
            self._ensure_large_setting_value_column(db)
            record = db.query(SystemSetting).filter(SystemSetting.setting_key == "factor_catalog_json").first()
            payload_json = json.dumps(cleaned, ensure_ascii=False, separators=(",", ":"))
            if record is None:
                record = SystemSetting(
                    setting_key="factor_catalog_json",
                    setting_name="常规水质因子字典",
                    setting_group="factor",
                    description="维护因子配置下拉框中的常规水质因子字典。",
                    setting_value=payload_json,
                )
                db.add(record)
            else:
                record.setting_value = payload_json
            db.commit()
        return self.fetch_factor_catalog()

    def create_site(self, payload: dict) -> dict:
        site_code = str(payload.get("site_code", "")).strip()
        site_name = str(payload.get("site_name", "")).strip()
        if not site_code:
            raise ValueError("site_code 不能为空")
        if not site_name:
            raise ValueError("site_name 不能为空")
        with SessionLocal() as db:
            existing = db.query(Site).filter(Site.site_code == site_code).first()
            if existing is not None:
                raise ValueError("site_code 已存在")
            site = Site(
                site_code=site_code,
                site_name=site_name,
                contact_name=str(payload.get("contact_name", "")).strip() or None,
                contact_phone=str(payload.get("contact_phone", "")).strip() or None,
            )
            db.add(site)
            db.commit()
            db.refresh(site)
            return {
                "id": site.id,
                "site_code": site.site_code,
                "site_name": site.site_name,
                "contact_name": site.contact_name or "",
                "contact_phone": site.contact_phone or "",
            }

    def update_site(self, site_id: int, payload: dict) -> dict:
        site_code = str(payload.get("site_code", "")).strip()
        site_name = str(payload.get("site_name", "")).strip()
        if not site_code:
            raise ValueError("site_code 不能为空")
        if not site_name:
            raise ValueError("site_name 不能为空")
        with SessionLocal() as db:
            site = db.query(Site).filter(Site.id == site_id).first()
            if site is None:
                raise ValueError("site not found")
            existing = db.query(Site).filter(Site.site_code == site_code, Site.id != site_id).first()
            if existing is not None:
                raise ValueError("site_code 已存在")
            site.site_code = site_code
            site.site_name = site_name
            site.contact_name = str(payload.get("contact_name", "")).strip() or None
            site.contact_phone = str(payload.get("contact_phone", "")).strip() or None
            db.commit()
            db.refresh(site)
            return {
                "id": site.id,
                "site_code": site.site_code,
                "site_name": site.site_name,
                "contact_name": site.contact_name or "",
                "contact_phone": site.contact_phone or "",
            }

    def delete_site(self, site_id: int) -> None:
        with SessionLocal() as db:
            site = db.query(Site).filter(Site.id == site_id).first()
            if site is None:
                raise ValueError("site not found")
            bound_count = db.query(func.count(Device.id)).filter(Device.site_id == site_id).scalar() or 0
            if bound_count > 0:
                raise ValueError("该站点下仍有关联设备，不能删除")
            db.delete(site)
            db.commit()

    def fetch_acquisition_settings(self) -> AcquisitionSettings:
        with SessionLocal() as db:
            settings = {
                row.setting_key: row.setting_value
                for row in db.query(SystemSetting)
                .filter(
                    SystemSetting.setting_key.in_(
                        [
                            "default_protocol",
                            "default_connection",
                            "default_config_template",
                            "collect_timeout_seconds",
                        ]
                    )
                )
                .all()
            }
            return AcquisitionSettings(
                default_protocol=settings.get("default_protocol", "modbus_tcp"),
                default_connection=settings.get("default_connection", "tcp"),
                default_config_template=settings.get("default_config_template", '{"host": "192.168.1.10", "port": 502, "slave": 1}'),
                collect_timeout_seconds=int(settings.get("collect_timeout_seconds", "5")),
            )

    def fetch_serial_settings(self) -> SerialSettings:
        with SessionLocal() as db:
            settings = {
                row.setting_key: row.setting_value
                for row in db.query(SystemSetting)
                .filter(
                    SystemSetting.setting_key.in_(
                        [
                            "serial_port_name",
                            "serial_baudrate",
                            "serial_data_bits",
                            "serial_parity",
                            "serial_stop_bits",
                            "serial_slave_address",
                        ]
                    )
                )
                .all()
            }
            return SerialSettings(
                port_name=settings.get("serial_port_name", "COM1"),
                baudrate=int(settings.get("serial_baudrate", "9600")),
                data_bits=int(settings.get("serial_data_bits", "8")),
                parity=settings.get("serial_parity", "N"),
                stop_bits=int(settings.get("serial_stop_bits", "1")),
                slave_address=int(settings.get("serial_slave_address", "1")),
            )

    def fetch_serial_profiles(self) -> list[SerialProfile]:
        current_settings = self.fetch_serial_settings()
        with SessionLocal() as db:
            self._ensure_large_setting_value_column(db)
            record = db.query(SystemSetting).filter(SystemSetting.setting_key == "serial_profiles_json").first()
            if record is None or not str(record.setting_value).strip():
                return self._build_default_serial_profiles(current_settings)
            payload = json.loads(record.setting_value)
        profiles: list[SerialProfile] = []
        for item in payload:
            profiles.append(
                SerialProfile(
                    profile_name=str(item.get("profile_name", "")).strip() or "未命名串口",
                    port_name=str(item.get("port_name", "COM1")).strip() or "COM1",
                    baudrate=int(item.get("baudrate", 9600)),
                    data_bits=int(item.get("data_bits", 8)),
                    parity=str(item.get("parity", "N")).strip().upper() or "N",
                    stop_bits=int(item.get("stop_bits", 1)),
                    slave_address=int(item.get("slave_address", 1)),
                    is_default=bool(item.get("is_default", False)),
                )
            )
        if not profiles:
            return self._build_default_serial_profiles(current_settings)
        if not any(profile.is_default for profile in profiles):
            profiles[0].is_default = True
        return profiles

    def fetch_acquisition_profiles(self) -> list[AcquisitionProfile]:
        current_settings = self.fetch_acquisition_settings()
        with SessionLocal() as db:
            self._ensure_large_setting_value_column(db)
            record = db.query(SystemSetting).filter(SystemSetting.setting_key == "acquisition_profiles_json").first()
            if record is None or not str(record.setting_value).strip():
                return self._build_default_acquisition_profiles(current_settings)
            payload = json.loads(record.setting_value)
        profiles: list[AcquisitionProfile] = []
        for item in payload:
            protocol_type = self._normalize_protocol_type(str(item.get("protocol_type", "")))
            profiles.append(
                AcquisitionProfile(
                    profile_name=str(item.get("profile_name", protocol_type)).strip() or protocol_type,
                    protocol_type=protocol_type,
                    connection_type=self._normalize_connection_type(str(item.get("connection_type", ""))),
                    serial_profile_name=str(item.get("serial_profile_name", "")).strip(),
                    collect_timeout_seconds=int(item.get("collect_timeout_seconds", 5)),
                    data_type=str(item.get("data_type", self._default_data_type(protocol_type))).strip() or self._default_data_type(protocol_type),
                    register_address=str(item.get("register_address", "40001")).strip(),
                    is_default=bool(item.get("is_default", False)),
                )
            )
        if not profiles:
            return self._build_default_acquisition_profiles(current_settings)
        if not any(profile.is_default for profile in profiles):
            fallback = next((profile for profile in profiles if profile.protocol_type == current_settings.default_protocol), profiles[0])
            fallback.is_default = True
        return profiles

    def save_acquisition_settings(
        self,
        default_protocol: str,
        default_connection: str,
        default_config_template: str,
        collect_timeout_seconds: int,
    ) -> AcquisitionSettings:
        if collect_timeout_seconds <= 0:
            raise ValueError("采集超时必须大于 0 秒")
        normalized_template = self._normalize_device_config(default_config_template)
        with SessionLocal() as db:
            definitions = {
                "default_protocol": ("默认协议类型", "acquisition", "新增传感器时默认使用的协议类型。", self._normalize_protocol_type(default_protocol)),
                "default_connection": ("默认连接方式", "acquisition", "新增传感器时默认使用的连接方式。", self._normalize_connection_type(default_connection)),
                "default_config_template": ("默认连接模板", "acquisition", "新增传感器时默认填充的连接配置模板。", normalized_template or "{}"),
                "collect_timeout_seconds": ("采集超时时间", "acquisition", "采集传感器时的默认超时时间，单位秒。", str(int(collect_timeout_seconds))),
            }
            records = {
                row.setting_key: row
                for row in db.query(SystemSetting).filter(SystemSetting.setting_key.in_(definitions.keys())).all()
            }
            for key, (name, group, description, value) in definitions.items():
                if key not in records:
                    records[key] = SystemSetting(
                        setting_key=key,
                        setting_name=name,
                        setting_group=group,
                        description=description,
                        setting_value=value,
                    )
                    db.add(records[key])
                records[key].setting_value = value
            db.commit()
        return self.fetch_acquisition_settings()

    def save_acquisition_profile(
        self,
        profile_name: str,
        protocol_type: str,
        connection_type: str,
        serial_profile_name: str,
        collect_timeout_seconds: int,
        data_type: str,
        register_address: str,
        is_default: bool,
        original_name: str | None = None,
    ) -> list[AcquisitionProfile]:
        normalized_name = profile_name.strip()
        if not normalized_name:
            raise ValueError("设备名称不能为空")
        normalized_protocol = self._normalize_protocol_type(protocol_type)
        if normalized_protocol not in {"modbus_tcp", "modbus_rtu"}:
            raise ValueError("当前仅支持 modbus_tcp 和 modbus_rtu")
        normalized_connection = self._normalize_connection_type(connection_type)
        normalized_serial_profile_name = serial_profile_name.strip()
        normalized_data_type = data_type.strip().lower()
        normalized_register_address = register_address.strip()
        normalized_register_address = self._normalize_register_address(normalized_register_address, field_label="寄存器地址")
        if collect_timeout_seconds <= 0:
            raise ValueError("采集超时必须大于 0 秒")
        if not normalized_data_type:
            raise ValueError("数据类型不能为空")
        if not normalized_register_address:
            raise ValueError("寄存器地址不能为空")
        if normalized_protocol == "modbus_rtu":
            if not normalized_serial_profile_name:
                raise ValueError("modbus_rtu 必须绑定串口配置名称")
            serial_profiles = self.fetch_serial_profiles()
            if not any(profile.profile_name == normalized_serial_profile_name for profile in serial_profiles):
                raise ValueError("绑定的串口配置不存在")
        else:
            normalized_serial_profile_name = ""
        if normalized_protocol == "modbus_rtu":
            bound_serial_profile = next(profile for profile in self.fetch_serial_profiles() if profile.profile_name == normalized_serial_profile_name)
            normalized_config = json.dumps(
                {
                    "serial_port": bound_serial_profile.port_name,
                    "baudrate": bound_serial_profile.baudrate,
                    "data_bits": bound_serial_profile.data_bits,
                    "parity": bound_serial_profile.parity,
                    "stopbits": bound_serial_profile.stop_bits,
                    "slave": bound_serial_profile.slave_address,
                },
                ensure_ascii=False,
            )
        else:
            normalized_config = json.dumps({"host": "192.168.1.10", "port": 502, "slave": 1}, ensure_ascii=False)

        profiles = self.fetch_acquisition_profiles()
        compare_name = (original_name or normalized_name).strip()
        target = next((profile for profile in profiles if profile.profile_name == compare_name), None)
        duplicate = next((profile for profile in profiles if profile.profile_name == normalized_name and profile.profile_name != compare_name), None)
        if duplicate is not None:
            raise ValueError("设备名称已存在")
        if target is None:
            profiles.append(
                AcquisitionProfile(
                    profile_name=normalized_name,
                    protocol_type=normalized_protocol,
                    connection_type=normalized_connection,
                    serial_profile_name=normalized_serial_profile_name,
                    collect_timeout_seconds=collect_timeout_seconds,
                    data_type=normalized_data_type,
                    register_address=normalized_register_address,
                    is_default=is_default,
                )
            )
        else:
            target.profile_name = normalized_name
            target.connection_type = normalized_connection
            target.protocol_type = normalized_protocol
            target.serial_profile_name = normalized_serial_profile_name
            target.collect_timeout_seconds = collect_timeout_seconds
            target.data_type = normalized_data_type
            target.register_address = normalized_register_address
            target.is_default = is_default

        if is_default:
            for profile in profiles:
                if profile.profile_name != normalized_name:
                    profile.is_default = False
        elif not any(profile.is_default for profile in profiles):
            profiles[0].is_default = True

        default_profile = next(profile for profile in profiles if profile.is_default)
        self.save_acquisition_settings(
            default_profile.protocol_type,
            default_profile.connection_type,
            normalized_config if default_profile.profile_name == normalized_name else (
                json.dumps(
                    {
                        "serial_port": next((item.port_name for item in self.fetch_serial_profiles() if item.profile_name == default_profile.serial_profile_name), "COM1"),
                        "baudrate": next((item.baudrate for item in self.fetch_serial_profiles() if item.profile_name == default_profile.serial_profile_name), 9600),
                        "data_bits": next((item.data_bits for item in self.fetch_serial_profiles() if item.profile_name == default_profile.serial_profile_name), 8),
                        "parity": next((item.parity for item in self.fetch_serial_profiles() if item.profile_name == default_profile.serial_profile_name), "N"),
                        "stopbits": next((item.stop_bits for item in self.fetch_serial_profiles() if item.profile_name == default_profile.serial_profile_name), 1),
                        "slave": next((item.slave_address for item in self.fetch_serial_profiles() if item.profile_name == default_profile.serial_profile_name), 1),
                    },
                    ensure_ascii=False,
                )
                if default_profile.protocol_type == "modbus_rtu"
                else json.dumps({"host": "192.168.1.10", "port": 502, "slave": 1}, ensure_ascii=False)
            ),
            default_profile.collect_timeout_seconds,
        )

        with SessionLocal() as db:
            self._ensure_large_setting_value_column(db)
            record = db.query(SystemSetting).filter(SystemSetting.setting_key == "acquisition_profiles_json").first()
            payload = json.dumps(
                [
                    {
                        "profile_name": profile.profile_name,
                        "protocol_type": profile.protocol_type,
                        "connection_type": profile.connection_type,
                        "serial_profile_name": profile.serial_profile_name,
                        "collect_timeout_seconds": profile.collect_timeout_seconds,
                        "data_type": profile.data_type,
                        "register_address": profile.register_address,
                        "is_default": profile.is_default,
                    }
                    for profile in profiles
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            if record is None:
                record = SystemSetting(
                    setting_key="acquisition_profiles_json",
                    setting_name="采集协议模板",
                    setting_group="acquisition",
                    description="维护 Modbus TCP/RTU 采集模板与寄存器地址模板。",
                    setting_value=payload,
                )
                db.add(record)
            else:
                record.setting_value = payload
            db.commit()
        return self.fetch_acquisition_profiles()

    def delete_acquisition_profile(self, profile_name: str) -> list[AcquisitionProfile]:
        profiles = self.fetch_acquisition_profiles()
        remaining = [profile for profile in profiles if profile.profile_name != profile_name]
        if len(remaining) == len(profiles):
            raise ValueError("profile not found")
        if not remaining:
            raise ValueError("至少保留一个采集模板")
        if not any(profile.is_default for profile in remaining):
            remaining[0].is_default = True
        default_profile = next(profile for profile in remaining if profile.is_default)
        if default_profile.protocol_type == "modbus_rtu":
            serial_profiles = self.fetch_serial_profiles()
            bound = next((item for item in serial_profiles if item.profile_name == default_profile.serial_profile_name), None)
            default_config = json.dumps(
                {
                    "serial_port": bound.port_name if bound else "COM1",
                    "baudrate": bound.baudrate if bound else 9600,
                    "data_bits": bound.data_bits if bound else 8,
                    "parity": bound.parity if bound else "N",
                    "stopbits": bound.stop_bits if bound else 1,
                    "slave": bound.slave_address if bound else 1,
                },
                ensure_ascii=False,
            )
        else:
            default_config = json.dumps({"host": "192.168.1.10", "port": 502, "slave": 1}, ensure_ascii=False)
        self.save_acquisition_settings(
            default_profile.protocol_type,
            default_profile.connection_type,
            default_config,
            default_profile.collect_timeout_seconds,
        )
        with SessionLocal() as db:
            self._ensure_large_setting_value_column(db)
            record = db.query(SystemSetting).filter(SystemSetting.setting_key == "acquisition_profiles_json").first()
            payload = json.dumps(
                [
                    {
                        "profile_name": profile.profile_name,
                        "protocol_type": profile.protocol_type,
                        "connection_type": profile.connection_type,
                        "serial_profile_name": profile.serial_profile_name,
                        "collect_timeout_seconds": profile.collect_timeout_seconds,
                        "data_type": profile.data_type,
                        "register_address": profile.register_address,
                        "is_default": profile.is_default,
                    }
                    for profile in remaining
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            if record is None:
                record = SystemSetting(
                    setting_key="acquisition_profiles_json",
                    setting_name="采集协议模板",
                    setting_group="acquisition",
                    description="维护 Modbus TCP/RTU 采集模板与寄存器地址模板。",
                    setting_value=payload,
                )
                db.add(record)
            else:
                record.setting_value = payload
            db.commit()
        return self.fetch_acquisition_profiles()

    def save_serial_settings(
        self,
        port_name: str,
        baudrate: int,
        data_bits: int,
        parity: str,
        stop_bits: int,
        slave_address: int,
    ) -> SerialSettings:
        if not port_name.strip():
            raise ValueError("串口号不能为空")
        if baudrate <= 0:
            raise ValueError("波特率必须大于 0")
        if slave_address <= 0:
            raise ValueError("设备地址必须大于 0")
        with SessionLocal() as db:
            definitions = {
                "serial_port_name": ("默认串口号", "serial", "采集传感器默认串口号。", port_name.strip()),
                "serial_baudrate": ("默认波特率", "serial", "采集传感器默认波特率。", str(int(baudrate))),
                "serial_data_bits": ("默认数据位", "serial", "采集传感器默认数据位。", str(int(data_bits))),
                "serial_parity": ("默认校验位", "serial", "采集传感器默认校验位。", parity.strip().upper() or "N"),
                "serial_stop_bits": ("默认停止位", "serial", "采集传感器默认停止位。", str(int(stop_bits))),
                "serial_slave_address": ("默认设备地址", "serial", "采集传感器默认设备地址。", str(int(slave_address))),
            }
            records = {
                row.setting_key: row
                for row in db.query(SystemSetting).filter(SystemSetting.setting_key.in_(definitions.keys())).all()
            }
            for key, (name, group, description, value) in definitions.items():
                if key not in records:
                    records[key] = SystemSetting(
                        setting_key=key,
                        setting_name=name,
                        setting_group=group,
                        description=description,
                        setting_value=value,
                    )
                    db.add(records[key])
                records[key].setting_value = value
            db.commit()
        return self.fetch_serial_settings()

    def save_serial_profile(
        self,
        profile_name: str,
        port_name: str,
        baudrate: int,
        data_bits: int,
        parity: str,
        stop_bits: int,
        slave_address: int,
        is_default: bool,
        original_name: str | None = None,
    ) -> list[SerialProfile]:
        normalized_name = profile_name.strip()
        if not normalized_name:
            raise ValueError("串口配置名称不能为空")
        if not port_name.strip():
            raise ValueError("串口号不能为空")
        if baudrate <= 0:
            raise ValueError("波特率必须大于 0")
        if slave_address <= 0:
            raise ValueError("设备地址必须大于 0")
        profiles = self.fetch_serial_profiles()
        compare_name = (original_name or normalized_name).strip()
        target = next((profile for profile in profiles if profile.profile_name == compare_name), None)
        duplicate = next((profile for profile in profiles if profile.profile_name == normalized_name and profile.profile_name != compare_name), None)
        if duplicate is not None:
            raise ValueError("串口配置名称已存在")
        if target is None:
            profiles.append(
                SerialProfile(
                    profile_name=normalized_name,
                    port_name=port_name.strip(),
                    baudrate=int(baudrate),
                    data_bits=int(data_bits),
                    parity=parity.strip().upper() or "N",
                    stop_bits=int(stop_bits),
                    slave_address=int(slave_address),
                    is_default=is_default,
                )
            )
        else:
            target.profile_name = normalized_name
            target.port_name = port_name.strip()
            target.baudrate = int(baudrate)
            target.data_bits = int(data_bits)
            target.parity = parity.strip().upper() or "N"
            target.stop_bits = int(stop_bits)
            target.slave_address = int(slave_address)
            target.is_default = is_default
        if is_default:
            for profile in profiles:
                if profile.profile_name != normalized_name:
                    profile.is_default = False
        elif not any(profile.is_default for profile in profiles):
            profiles[0].is_default = True

        default_profile = next(profile for profile in profiles if profile.is_default)
        self.save_serial_settings(
            default_profile.port_name,
            default_profile.baudrate,
            default_profile.data_bits,
            default_profile.parity,
            default_profile.stop_bits,
            default_profile.slave_address,
        )
        with SessionLocal() as db:
            self._ensure_large_setting_value_column(db)
            record = db.query(SystemSetting).filter(SystemSetting.setting_key == "serial_profiles_json").first()
            payload = json.dumps(
                [
                    {
                        "profile_name": profile.profile_name,
                        "port_name": profile.port_name,
                        "baudrate": profile.baudrate,
                        "data_bits": profile.data_bits,
                        "parity": profile.parity,
                        "stop_bits": profile.stop_bits,
                        "slave_address": profile.slave_address,
                        "is_default": profile.is_default,
                    }
                    for profile in profiles
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            if record is None:
                record = SystemSetting(
                    setting_key="serial_profiles_json",
                    setting_name="串口配置列表",
                    setting_group="serial",
                    description="维护多个串口接入配置。",
                    setting_value=payload,
                )
                db.add(record)
            else:
                record.setting_value = payload
            db.commit()
        return self.fetch_serial_profiles()

    def delete_serial_profile(self, profile_name: str) -> list[SerialProfile]:
        profiles = self.fetch_serial_profiles()
        bound_profiles = [
            profile.profile_name
            for profile in self.fetch_acquisition_profiles()
            if profile.protocol_type == "modbus_rtu" and profile.serial_profile_name == profile_name
        ]
        if bound_profiles:
            raise ValueError("当前串口配置已被设备设置中的 Modbus RTU 模板绑定，不能删除")
        remaining = [profile for profile in profiles if profile.profile_name != profile_name]
        if len(remaining) == len(profiles):
            raise ValueError("serial profile not found")
        if not remaining:
            raise ValueError("至少保留一个串口配置")
        if not any(profile.is_default for profile in remaining):
            remaining[0].is_default = True
        default_profile = next(profile for profile in remaining if profile.is_default)
        self.save_serial_settings(
            default_profile.port_name,
            default_profile.baudrate,
            default_profile.data_bits,
            default_profile.parity,
            default_profile.stop_bits,
            default_profile.slave_address,
        )
        with SessionLocal() as db:
            self._ensure_large_setting_value_column(db)
            record = db.query(SystemSetting).filter(SystemSetting.setting_key == "serial_profiles_json").first()
            payload = json.dumps(
                [
                    {
                        "profile_name": profile.profile_name,
                        "port_name": profile.port_name,
                        "baudrate": profile.baudrate,
                        "data_bits": profile.data_bits,
                        "parity": profile.parity,
                        "stop_bits": profile.stop_bits,
                        "slave_address": profile.slave_address,
                        "is_default": profile.is_default,
                    }
                    for profile in remaining
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            if record is None:
                record = SystemSetting(
                    setting_key="serial_profiles_json",
                    setting_name="串口配置列表",
                    setting_group="serial",
                    description="维护多个串口接入配置。",
                    setting_value=payload,
                )
                db.add(record)
            else:
                record.setting_value = payload
            db.commit()
        return self.fetch_serial_profiles()

    def fetch_device_protocol_options(self) -> list[str]:
        return ["mock", "modbus_tcp", "modbus_rtu", "custom"]

    def fetch_device_connection_options(self) -> list[str]:
        return ["tcp", "serial", "rs485", "custom"]

    def fetch_devices(self) -> list[dict]:
        with SessionLocal() as db:
            freshness_threshold_seconds = self._freshness_threshold_seconds_from_db(db)
            devices = (
                db.query(Device, Site.site_code, Site.site_name)
                .join(Site, Site.id == Device.site_id)
                .order_by(Device.sort_order.asc(), Device.id.asc())
                .all()
            )
            latest_map = self._latest_collected_map(db)
            metric_rows = db.query(DeviceMetric).order_by(DeviceMetric.sort_order.asc(), DeviceMetric.id.asc()).all()
            metric_map: dict[int, list[DeviceMetric]] = {}
            for row in metric_rows:
                metric_map.setdefault(row.device_id, []).append(row)
            rows: list[dict] = []
            for device, site_code, site_name in devices:
                device_metrics = metric_map.get(device.id, [])
                config_status, config_hint = self._device_config_summary(device, device_metrics)
                last_collected_at = latest_map.get(device.id)
                rows.append(
                    {
                        "id": device.id,
                        "site_id": device.site_id,
                        "site_code": site_code,
                        "site_name": site_name,
                        "pond_code": device.pond_code,
                        "device_code": device.device_code,
                        "device_name": device.device_name,
                        "device_type": device.device_type,
                        "protocol_type": device.protocol_type,
                        "connection_type": device.connection_type,
                        "status": self._resolve_device_status(last_collected_at, freshness_threshold_seconds),
                        "last_collected_at": last_collected_at.strftime("%Y-%m-%d %H:%M:%S") if last_collected_at else "",
                        "config_json": device.config_json or "",
                        "factor_count": len(device_metrics),
                        "factor_summary": _factor_summary_text(device_metrics),
                        "config_status": config_status,
                        "config_hint": config_hint,
                        "sort_order": device.sort_order,
                    }
                )
            return rows

    def create_device(self, payload: dict) -> dict:
        with SessionLocal() as db:
            required_keys = ["site_id", "pond_code", "device_code", "device_name", "device_type", "protocol_type", "connection_type"]
            for key in required_keys:
                if not str(payload.get(key, "")).strip():
                    raise ValueError(f"{key} 不能为空")

            existing = db.query(Device).filter(Device.device_code == str(payload["device_code"]).strip()).first()
            if existing is not None:
                raise ValueError("device_code 已存在")

            site = db.query(Site).filter(Site.id == int(payload["site_id"])).first()
            if site is None:
                raise ValueError("site not found")

            device = Device(
                site_id=site.id,
                pond_code=str(payload["pond_code"]).strip(),
                device_code=str(payload["device_code"]).strip(),
                device_name=str(payload["device_name"]).strip(),
                device_type=str(payload["device_type"]).strip(),
                protocol_type=self._normalize_protocol_type(str(payload["protocol_type"])),
                connection_type=self._normalize_connection_type(str(payload["connection_type"])),
                status="offline",
                config_json=self._normalize_device_config(str(payload.get("config_json", ""))) or None,
                sort_order=int(payload.get("sort_order", 0)),
            )
            db.add(device)
            db.commit()
            db.refresh(device)
            return {
                "id": device.id,
                "site_id": device.site_id,
                "site_code": site.site_code,
                "device_code": device.device_code,
                "device_name": device.device_name,
                "device_type": device.device_type,
                "protocol_type": device.protocol_type,
                "connection_type": device.connection_type,
                "sort_order": device.sort_order,
            }

    def fetch_device_metrics(self, device_id: int) -> list[dict]:
        with SessionLocal() as db:
            rows = (
                db.query(DeviceMetric)
                .filter(DeviceMetric.device_id == device_id)
                .order_by(DeviceMetric.sort_order.asc(), DeviceMetric.id.asc())
                .all()
            )
            return [
                {
                    "id": row.id,
                    "device_id": row.device_id,
                    "metric_code": row.metric_code,
                    "metric_name": row.metric_name,
                    "metric_unit": row.metric_unit or "",
                    "lower_limit": float(row.lower_limit) if row.lower_limit is not None else None,
                    "upper_limit": float(row.upper_limit) if row.upper_limit is not None else None,
                    "register_address": row.register_address or "",
                    "sort_order": row.sort_order,
                }
                for row in rows
            ]

    def save_device_metrics(self, device_id: int, payload: list[dict]) -> list[dict]:
        with SessionLocal() as db:
            device = db.query(Device).filter(Device.id == device_id).first()
            if device is None:
                raise ValueError("device not found")
            metric_map = {
                row.id: row
                for row in db.query(DeviceMetric).filter(DeviceMetric.device_id == device_id).all()
            }
            for item in payload:
                metric_id = int(item.get("id", 0))
                metric = metric_map.get(metric_id)
                if metric is None:
                    raise ValueError("metric not found")
                lower_limit = self._parse_optional_float(item.get("lower_limit"))
                upper_limit = self._parse_optional_float(item.get("upper_limit"))
                if lower_limit is not None and upper_limit is not None and lower_limit > upper_limit:
                    raise ValueError(f"{metric.metric_name} 的下限不能大于上限")
                metric.lower_limit = lower_limit
                metric.upper_limit = upper_limit
                metric.register_address = str(item.get("register_address", "")).strip() or None
                metric.sort_order = int(item.get("sort_order", metric.sort_order or 0))
            db.commit()
        return self.fetch_device_metrics(device_id)

    def save_factor_bindings(self, device_id: int, payload: list[dict]) -> list[dict]:
        with SessionLocal() as db:
            device = db.query(Device).filter(Device.id == device_id).first()
            if device is None:
                raise ValueError("device not found")
            factor_catalog = {
                str(item.get("code", "")).strip(): item
                for item in self.fetch_factor_catalog()
                if str(item.get("code", "")).strip()
            }

            existing_rows = {
                row.id: row
                for row in db.query(DeviceMetric).filter(DeviceMetric.device_id == device_id).all()
            }
            keep_ids: set[int] = set()
            seen_metric_codes: set[str] = set()

            for sort_order, item in enumerate(payload, start=1):
                metric_code = str(item.get("metric_code", "")).strip()
                if not metric_code:
                    raise ValueError("因子编码不能为空")
                factor = factor_catalog.get(metric_code)
                if factor is None:
                    raise ValueError(f"未找到因子字典配置：{metric_code}")
                metric_name = str(factor.get("name", "")).strip()
                if not metric_name:
                    raise ValueError(f"因子字典缺少名称：{metric_code}")
                if metric_code in seen_metric_codes:
                    raise ValueError(f"{metric_name} 存在重复绑定")
                seen_metric_codes.add(metric_code)

                lower_limit = self._parse_optional_float(item.get("lower_limit"))
                upper_limit = self._parse_optional_float(item.get("upper_limit"))
                if lower_limit is not None and upper_limit is not None and lower_limit > upper_limit:
                    raise ValueError(f"{metric_name} 的下限不能大于上限")

                metric_id = int(item.get("id", 0) or 0)
                metric = existing_rows.get(metric_id)
                if metric is None:
                    metric = DeviceMetric(device_id=device_id)
                    db.add(metric)
                else:
                    keep_ids.add(metric.id)

                metric.metric_code = metric_code
                metric.metric_name = metric_name
                metric.metric_unit = str(factor.get("unit", "")).strip() or None
                metric.lower_limit = lower_limit
                metric.upper_limit = upper_limit
                metric.sort_order = sort_order

            delete_ids = [
                row_id
                for row_id in existing_rows
                if row_id not in keep_ids and row_id not in {int(item.get("id", 0) or 0) for item in payload}
            ]
            for row_id in delete_ids:
                db.delete(existing_rows[row_id])

            db.commit()
        return self.fetch_device_metrics(device_id)

    def fetch_device_template_candidates(self, device_type: str = "", exclude_device_id: int | None = None) -> list[dict]:
        with SessionLocal() as db:
            query = db.query(Device)
            if device_type.strip():
                query = query.filter(Device.device_type == device_type.strip())
            if exclude_device_id is not None:
                query = query.filter(Device.id != exclude_device_id)
            devices = query.order_by(Device.device_type.asc(), Device.sort_order.asc(), Device.id.asc()).all()
            return [
                {
                    "id": device.id,
                    "device_code": device.device_code,
                    "device_name": device.device_name,
                    "device_type": device.device_type,
                    "protocol_type": device.protocol_type,
                    "connection_type": device.connection_type,
                }
                for device in devices
            ]

    def copy_device_configuration(self, source_device_id: int, target_device_id: int) -> dict:
        with SessionLocal() as db:
            source = db.query(Device).filter(Device.id == source_device_id).first()
            target = db.query(Device).filter(Device.id == target_device_id).first()
            if source is None or target is None:
                raise ValueError("device not found")
            if source.id == target.id:
                raise ValueError("source and target device must be different")

            target.device_type = source.device_type
            target.protocol_type = source.protocol_type
            target.connection_type = source.connection_type
            target.config_json = source.config_json
            db.commit()
            db.refresh(target)
            return {
                "id": target.id,
                "device_code": target.device_code,
                "device_name": target.device_name,
                "device_type": target.device_type,
                "protocol_type": target.protocol_type,
                "connection_type": target.connection_type,
                "config_json": target.config_json or "",
            }

    def copy_factor_bindings(self, source_device_id: int, target_device_id: int) -> list[dict]:
        with SessionLocal() as db:
            source = db.query(Device).filter(Device.id == source_device_id).first()
            target = db.query(Device).filter(Device.id == target_device_id).first()
            if source is None or target is None:
                raise ValueError("device not found")
            if source.id == target.id:
                raise ValueError("source and target device must be different")

            source_rows = (
                db.query(DeviceMetric)
                .filter(DeviceMetric.device_id == source_device_id)
                .order_by(DeviceMetric.sort_order.asc(), DeviceMetric.id.asc())
                .all()
            )
            if not source_rows:
                raise ValueError("source device has no factor bindings")

            for row in db.query(DeviceMetric).filter(DeviceMetric.device_id == target_device_id).all():
                db.delete(row)

            for source_row in source_rows:
                db.add(
                    DeviceMetric(
                        device_id=target_device_id,
                        metric_code=source_row.metric_code,
                        metric_name=source_row.metric_name,
                        metric_unit=source_row.metric_unit,
                        lower_limit=source_row.lower_limit,
                        upper_limit=source_row.upper_limit,
                        register_address=source_row.register_address,
                        sort_order=source_row.sort_order,
                    )
                )

            db.commit()
        return self.fetch_device_metrics(target_device_id)

    def update_device(self, device_id: int, payload: dict) -> dict:
        with SessionLocal() as db:
            device = db.query(Device).filter(Device.id == device_id).first()
            if device is None:
                raise ValueError("device not found")

            required_keys = ["pond_code", "device_name", "protocol_type", "connection_type"]
            for key in required_keys:
                if not str(payload.get(key, "")).strip():
                    raise ValueError(f"{key} 不能为空")

            site_id = int(payload.get("site_id", device.site_id))
            site = db.query(Site).filter(Site.id == site_id).first()
            if site is None:
                raise ValueError("site not found")
            raw_config = self._normalize_device_config(str(payload.get("config_json", "")))

            device.site_id = site_id
            device.pond_code = str(payload["pond_code"]).strip()
            device.device_name = str(payload["device_name"]).strip()
            device.device_type = str(payload.get("device_type", device.device_type)).strip() or device.device_type
            device.protocol_type = self._normalize_protocol_type(str(payload["protocol_type"]))
            device.connection_type = self._normalize_connection_type(str(payload["connection_type"]))
            device.config_json = raw_config or None
            device.sort_order = int(payload.get("sort_order", device.sort_order or 0))
            db.commit()
            db.refresh(device)
            return {
                "id": device.id,
                "site_id": device.site_id,
                "site_code": site.site_code,
                "pond_code": device.pond_code,
                "device_name": device.device_name,
                "device_type": device.device_type,
                "protocol_type": device.protocol_type,
                "connection_type": device.connection_type,
                "config_json": device.config_json or "",
                "sort_order": device.sort_order,
            }

    def fetch_latest_telemetry(self, limit: int = 30) -> list[dict]:
        with SessionLocal() as db:
            rows = (
                db.query(TelemetryRecord, Device.device_name, Device.pond_code)
                .join(Device, Device.id == TelemetryRecord.device_id)
                .order_by(TelemetryRecord.collected_at.desc(), TelemetryRecord.id.desc())
                .limit(limit)
                .all()
            )
            result = []
            for telemetry, device_name, pond_code in rows:
                metric_value = telemetry.metric_value
                if isinstance(metric_value, Decimal):
                    metric_value = float(metric_value)
                result.append(
                    {
                        "device_id": telemetry.device_id,
                        "device_name": device_name,
                        "pond_code": pond_code,
                        "metric_name": telemetry.metric_name,
                        "metric_value": metric_value,
                        "metric_unit": telemetry.metric_unit or "",
                        "quality": telemetry.quality,
                        "collected_at": telemetry.collected_at.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
            return result

    def query_telemetry(
        self,
        *,
        pond_code: str = "",
        device_keyword: str = "",
        metric_keyword: str = "",
        start_date: str = "",
        end_date: str = "",
        granularity: str = "realtime",
        limit: int = 5000,
    ) -> list[dict]:
        with SessionLocal() as db:
            query = (
                db.query(TelemetryRecord, Device.device_name, Device.pond_code, Device.device_code)
                .join(Device, Device.id == TelemetryRecord.device_id)
            )
            if pond_code.strip():
                query = query.filter(Device.pond_code == pond_code.strip())
            if device_keyword.strip():
                keyword = f"%{device_keyword.strip()}%"
                query = query.filter(or_(Device.device_name.like(keyword), Device.device_code.like(keyword)))
            if metric_keyword.strip():
                keyword = f"%{metric_keyword.strip()}%"
                query = query.filter(or_(TelemetryRecord.metric_name.like(keyword), TelemetryRecord.metric_code.like(keyword)))

            start_dt = self._parse_query_datetime(start_date)
            end_dt = self._parse_query_datetime(end_date, end_of_day=True)
            if start_dt is not None:
                query = query.filter(TelemetryRecord.collected_at >= start_dt)
            if end_dt is not None:
                query = query.filter(TelemetryRecord.collected_at <= end_dt)

            rows = query.order_by(TelemetryRecord.collected_at.desc(), TelemetryRecord.id.desc()).limit(limit).all()
            if granularity == "realtime":
                result = []
                for telemetry, device_name, row_pond_code, device_code in rows:
                    metric_value = telemetry.metric_value
                    if isinstance(metric_value, Decimal):
                        metric_value = float(metric_value)
                    result.append(
                        {
                            "device_id": telemetry.device_id,
                            "device_code": device_code,
                            "device_name": device_name,
                            "pond_code": row_pond_code,
                            "metric_code": telemetry.metric_code,
                            "metric_name": telemetry.metric_name,
                            "metric_value": metric_value,
                            "metric_unit": telemetry.metric_unit or "",
                            "quality": telemetry.quality,
                            "collected_at": telemetry.collected_at.strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )
                return result

            grouped: dict[tuple[str, str, str, str, str], dict] = {}
            for telemetry, device_name, row_pond_code, device_code in rows:
                metric_value = float(telemetry.metric_value) if isinstance(telemetry.metric_value, Decimal) else float(telemetry.metric_value)
                bucket = self._bucket_time_text(telemetry.collected_at, granularity)
                key = (row_pond_code, device_code, device_name, telemetry.metric_code, bucket)
                entry = grouped.get(key)
                if entry is None:
                    grouped[key] = {
                        "pond_code": row_pond_code,
                        "device_code": device_code,
                        "device_name": device_name,
                        "metric_code": telemetry.metric_code,
                        "metric_name": telemetry.metric_name,
                        "metric_unit": telemetry.metric_unit or "",
                        "quality": telemetry.quality,
                        "collected_at": bucket,
                        "sum": metric_value,
                        "count": 1,
                    }
                else:
                    entry["sum"] += metric_value
                    entry["count"] += 1
                    if entry["quality"] != "warning" and telemetry.quality == "warning":
                        entry["quality"] = "warning"

            result = []
            for entry in sorted(grouped.values(), key=lambda item: item["collected_at"], reverse=True):
                count = entry.pop("count")
                total = entry.pop("sum")
                entry["metric_value"] = round(total / count, 2)
                result.append(entry)
            return result

    def export_latest_telemetry_csv(self, export_dir: str | Path, limit: int = 200) -> Path:
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)
        filename = f"telemetry_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = export_path / filename
        rows = self.fetch_latest_telemetry(limit=limit)
        with file_path.open("w", encoding="utf-8-sig", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(["设备ID", "设备名称", "塘口", "指标名称", "数值", "单位", "质量", "采集时间"])
            for row in rows:
                writer.writerow(
                    [
                        row["device_id"],
                        row["device_name"],
                        row["pond_code"],
                        row["metric_name"],
                        row["metric_value"],
                        row["metric_unit"],
                        row["quality"],
                        row["collected_at"],
                    ]
                )
        return file_path

    def export_query_rows_csv(self, export_dir: str | Path, rows: list[dict], granularity: str) -> Path:
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)
        filename = f"telemetry_{granularity}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = export_path / filename
        with file_path.open("w", encoding="utf-8-sig", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(["塘口", "设备编号", "设备名称", "因子编码", "因子名称", "数值", "单位", "质量", "时间"])
            for row in rows:
                writer.writerow(
                    [
                        row.get("pond_code", ""),
                        row.get("device_code", ""),
                        row.get("device_name", ""),
                        row.get("metric_code", ""),
                        row.get("metric_name", ""),
                        row.get("metric_value", ""),
                        row.get("metric_unit", ""),
                        row.get("quality", ""),
                        row.get("collected_at", ""),
                    ]
                )
        return file_path

    def fetch_recent_alerts(self, limit: int = 30) -> list[dict]:
        with SessionLocal() as db:
            rows = (
                db.query(AlertEvent, Device.device_name)
                .join(Device, Device.id == AlertEvent.device_id)
                .order_by(AlertEvent.triggered_at.desc(), AlertEvent.id.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": alert.id,
                    "device_name": device_name,
                    "alert_code": alert.alert_code,
                    "alert_level": alert.alert_level,
                    "status": alert.status,
                    "alert_message": alert.alert_message,
                    "triggered_at": alert.triggered_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "recovered_at": alert.recovered_at.strftime("%Y-%m-%d %H:%M:%S") if alert.recovered_at else "",
                }
                for alert, device_name in rows
            ]

    def fetch_upload_tasks(self, limit: int = 20) -> list[dict]:
        with SessionLocal() as db:
            rows = db.query(UploadTask).order_by(UploadTask.created_at.desc(), UploadTask.id.desc()).limit(limit).all()
            gateway_code = self.fetch_platform_settings().gateway_code
            result_rows = []
            for row in rows:
                try:
                    payload = json.loads(row.payload_json)
                except json.JSONDecodeError:
                    payload = {}
                data_time = payload.get("collected_at") or payload.get("hour_bucket") or ""
                result_rows.append(
                    {
                        "task_type": row.task_type,
                        "command_code": "2011" if row.task_type == "telemetry" else "2061",
                        "device_code": str(payload.get("device_code", "")),
                        "data_time": self._format_upload_time_text(data_time),
                        "status": row.status,
                        "retry_count": row.retry_count,
                        "result_text": self._upload_result_text(row),
                        "packet_preview": self._build_upload_packet_preview(row.task_type, payload, gateway_code),
                        "created_at": row.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
            return result_rows

    def fetch_upload_queue_status(self) -> UploadQueueStatus:
        with SessionLocal() as db:
            rows = (
                db.query(UploadTask.status, func.count(UploadTask.id))
                .group_by(UploadTask.status)
                .all()
            )
            counts = {status: int(count) for status, count in rows}
            pending_count = counts.get("pending", 0)
            failed_count = counts.get("failed", 0)
            skipped_count = counts.get("skipped", 0)
            uploaded_count = counts.get("uploaded", 0)
            summary = (
                f"离线缓存/补传：待上传 {pending_count} 条，失败待重试 {failed_count} 条，"
                f"重复跳过 {skipped_count} 条，已上传 {uploaded_count} 条。"
                "同一轮同指纹报文只发送一次，补传与重试不等于重复上传。"
            )
            return UploadQueueStatus(pending_count, failed_count, skipped_count, uploaded_count, summary)

    def fetch_runtime_settings(self) -> RuntimeSettings:
        with SessionLocal() as db:
            settings = {
                row.setting_key: row.setting_value
                for row in db.query(SystemSetting)
                .filter(SystemSetting.setting_key.in_(["auto_save_enabled", "save_interval_seconds"]))
                .all()
            }
            return RuntimeSettings(
                settings.get("auto_save_enabled", "1") == "1",
                normalize_save_interval_seconds(settings.get("save_interval_seconds", "30")),
            )

    def _runtime_interval_seconds_from_db(self, db) -> int:
        row = db.query(SystemSetting).filter(SystemSetting.setting_key == "save_interval_seconds").first()
        return normalize_save_interval_seconds(row.setting_value if row else "30")

    def _collect_once_for_interval(self, db, device: Device, save_interval_seconds: int):
        parameters = inspect.signature(collect_once).parameters
        if "save_interval_seconds" in parameters:
            return collect_once(db, device, save_interval_seconds=save_interval_seconds)
        return collect_once(db, device)

    def _fetch_analysis_thresholds(self, db) -> dict[str, AnalysisThreshold]:
        thresholds = dict(DEFAULT_ANALYSIS_THRESHOLDS)
        row = db.query(SystemSetting).filter(SystemSetting.setting_key == "analysis_thresholds_json").first()
        if row is None or not row.setting_value.strip():
            return thresholds
        try:
            payload = json.loads(row.setting_value)
        except json.JSONDecodeError:
            return thresholds
        for code, config in payload.items():
            if not isinstance(config, dict):
                continue
            current = thresholds.get(str(code), AnalysisThreshold(None, None, "", "自定义阈值"))
            thresholds[str(code)] = AnalysisThreshold(
                lower=config.get("lower", current.lower),
                upper=config.get("upper", current.upper),
                advice=str(config.get("advice", current.advice)),
                source=str(config.get("source", current.source)),
            )
        return thresholds

    def _fetch_analysis_quality_rules(self, db) -> dict:
        rules = dict(DEFAULT_ANALYSIS_QUALITY_RULES)
        row = db.query(SystemSetting).filter(SystemSetting.setting_key == "analysis_quality_rules_json").first()
        if row is None or not row.setting_value.strip():
            return rules
        try:
            payload = json.loads(row.setting_value)
        except json.JSONDecodeError:
            return rules
        if isinstance(payload, dict):
            rules.update(payload)
        return rules

    def _analysis_status(self, latest_value: float | None, threshold: AnalysisThreshold | None) -> str:
        if latest_value is None or threshold is None:
            return "unknown"
        if threshold.lower is not None and latest_value < float(threshold.lower):
            return "warning"
        if threshold.upper is not None and latest_value > float(threshold.upper):
            return "warning"
        return "good"

    def _analysis_trend(self, values: list[float]) -> str:
        if len(values) < 2:
            return "样本不足"
        delta = values[-1] - values[0]
        if abs(delta) < 0.05:
            return "基本稳定"
        return "上升" if delta > 0 else "下降"

    def _sparkline(self, values: list[float]) -> str:
        if not values:
            return "暂无"
        recent = values[-12:]
        low = min(recent)
        high = max(recent)
        blocks = "▁▂▃▄▅▆▇█"
        if high == low:
            return blocks[3] * len(recent)
        return "".join(blocks[round((value - low) / (high - low) * (len(blocks) - 1))] for value in recent)

    def _quality_tips(self, values: list[float], latest_value: float | None, threshold: AnalysisThreshold | None, rules: dict) -> list[str]:
        tips: list[str] = []
        if latest_value is None:
            return tips
        if threshold is not None:
            if threshold.lower is not None and latest_value < float(threshold.lower):
                tips.append("超标：低于下限")
            if threshold.upper is not None and latest_value > float(threshold.upper):
                tips.append("超标：高于上限")
        constant_min_samples = int(rules.get("constant_min_samples", 5))
        constant_delta = float(rules.get("constant_delta", 0.01))
        if len(values) >= constant_min_samples and max(values[-constant_min_samples:]) - min(values[-constant_min_samples:]) <= constant_delta:
            tips.append("疑似恒值：请检查传感器是否卡值")
        outlier_min_samples = int(rules.get("outlier_min_samples", 5))
        outlier_delta_ratio = float(rules.get("outlier_delta_ratio", 0.25))
        if len(values) >= outlier_min_samples:
            baseline_values = values[:-1] or values
            baseline = sum(baseline_values) / len(baseline_values)
            denominator = max(abs(baseline), 1.0)
            if abs(latest_value - baseline) / denominator >= outlier_delta_ratio:
                tips.append("疑似离群：建议复测并校准探头")
        return tips

    def fetch_analysis_summary(self, window_hours: int = 24) -> AnalysisSummary:
        window_start = datetime.now() - timedelta(hours=window_hours)
        focus_codes = {"w01010", "w01014", "w01001", "w01019", "w01003", "w01018", "w21003", "w21011", "w21001"}
        with SessionLocal() as db:
            thresholds = self._fetch_analysis_thresholds(db)
            quality_rules = self._fetch_analysis_quality_rules(db)
            rows = (
                db.query(TelemetryRecord)
                .filter(TelemetryRecord.collected_at >= window_start)
                .filter(TelemetryRecord.metric_code.in_(focus_codes))
                .order_by(TelemetryRecord.metric_code.asc(), TelemetryRecord.collected_at.asc(), TelemetryRecord.id.asc())
                .all()
            )
            grouped: dict[str, list[TelemetryRecord]] = {}
            for row in rows:
                grouped.setdefault(row.metric_code, []).append(row)
            metrics: list[MetricAnalysis] = []
            for code in sorted(focus_codes):
                samples = grouped.get(code, [])
                threshold = thresholds.get(code)
                if samples:
                    values = [float(row.metric_value) for row in samples]
                    latest = samples[-1]
                    latest_value = float(latest.metric_value)
                    metric_name = latest.metric_name
                    metric_unit = latest.metric_unit or ""
                    latest_time = latest.collected_at.strftime("%Y-%m-%d %H:%M:%S")
                    min_value = min(values)
                    max_value = max(values)
                    avg_value = round(sum(values) / len(values), 3)
                    trend = self._analysis_trend(values)
                    status = self._analysis_status(latest_value, threshold)
                    quality_tips = self._quality_tips(values, latest_value, threshold, quality_rules)
                    advice = threshold.advice if threshold else "暂无阈值，请先配置分析阈值。"
                    if status == "good":
                        advice = "当前处于建议区间，继续保持巡检和传感器校准。"
                    if quality_tips and status == "good":
                        status = "warning"
                else:
                    default_factor = next((item for item in DEFAULT_WATER_FACTORS if item["code"] == code), {"name": code, "unit": ""})
                    latest_value = None
                    metric_name = default_factor["name"]
                    metric_unit = default_factor["unit"]
                    latest_time = ""
                    min_value = max_value = avg_value = None
                    trend = "暂无数据"
                    status = "unknown"
                    quality_tips = []
                    advice = "暂无最近数据，建议先完成采集或检查设备绑定。"
                metrics.append(
                    MetricAnalysis(
                        metric_code=code,
                        metric_name=metric_name,
                        metric_unit=metric_unit,
                        latest_value=latest_value,
                        min_value=min_value,
                        max_value=max_value,
                        avg_value=avg_value,
                        sample_count=len(samples),
                        trend=trend,
                        status=status,
                        advice=advice,
                        quality_tip="；".join(quality_tips) if quality_tips else "未发现明显质量问题",
                        latest_time=latest_time,
                        sparkline=self._sparkline(values) if samples else "暂无",
                    )
                )
            return AnalysisSummary(
                generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                window_hours=window_hours,
                metrics=metrics,
                thresholds=thresholds,
            )

    def save_runtime_settings(self, auto_save_enabled: bool, save_interval_seconds: int) -> RuntimeSettings:
        if save_interval_seconds not in ALLOWED_SAVE_INTERVAL_SECONDS:
            raise ValueError("实时保存间隔只能选择 30 秒或 60 秒")
        with SessionLocal() as db:
            records = {
                row.setting_key: row
                for row in db.query(SystemSetting)
                .filter(SystemSetting.setting_key.in_(["auto_save_enabled", "save_interval_seconds"]))
                .all()
            }
            if "auto_save_enabled" not in records:
                records["auto_save_enabled"] = SystemSetting(
                    setting_key="auto_save_enabled",
                    setting_name="启用实时入库",
                    setting_group="runtime",
                    description="控制是否启用自动采集并实时写入数据库。",
                    setting_value="1",
                )
                db.add(records["auto_save_enabled"])
            if "save_interval_seconds" not in records:
                records["save_interval_seconds"] = SystemSetting(
                    setting_key="save_interval_seconds",
                    setting_name="实时保存间隔",
                    setting_group="runtime",
                    description="自动采集并实时写入数据库的时间间隔，单位秒。",
                    setting_value="30",
                )
                db.add(records["save_interval_seconds"])
            records["auto_save_enabled"].setting_value = "1" if auto_save_enabled else "0"
            records["save_interval_seconds"].setting_value = str(save_interval_seconds)
            db.commit()
        return RuntimeSettings(auto_save_enabled, save_interval_seconds)

    def trigger_collect(self, device_id: int) -> dict:
        with SessionLocal() as db:
            device = db.query(Device).filter(Device.id == device_id).first()
            if device is None:
                raise ValueError("device not found")
            metrics = (
                db.query(DeviceMetric)
                .filter(DeviceMetric.device_id == device_id)
                .order_by(DeviceMetric.sort_order.asc(), DeviceMetric.id.asc())
                .all()
            )
            config_status, config_hint = self._device_config_summary(device, metrics)
            if config_status != "已完成":
                raise ValueError(f"当前设备配置未完成，暂不能试采：{config_hint}")
            result = self._collect_once_for_interval(db, device, self._runtime_interval_seconds_from_db(db))
            device.status = "online"
            db.commit()
            return {
                "device_id": result.device_id,
                "device_code": result.device_code,
                "metric_count": len(result.metrics),
                "collected_at": result.collected_at.strftime("%Y-%m-%d %H:%M:%S"),
            }

    def upload_pending_tasks(self) -> dict:
        with SessionLocal() as db:
            return upload_pending_records(db)

    def retry_failed_upload_tasks(self) -> dict:
        with SessionLocal() as db:
            return reset_failed_upload_tasks(db)

    def auto_collect_all_devices(self) -> dict:
        with SessionLocal() as db:
            devices = db.query(Device).order_by(Device.sort_order.asc(), Device.id.asc()).all()
            before_ids = {
                row_id
                for (row_id,) in db.query(UploadTask.id)
                .filter(UploadTask.status == "pending")
                .all()
            }
            result = self._collect_devices(db, devices)
            new_task_ids = [
                row_id
                for (row_id,) in db.query(UploadTask.id)
                .filter(UploadTask.status == "pending")
                .order_by(UploadTask.id.asc())
                .all()
                if row_id not in before_ids
            ]
            upload_result = {"processed": 0, "uploaded": 0, "failed": 0}
            if new_task_ids:
                upload_result = upload_pending_records(db, task_ids=new_task_ids, max_tasks=len(new_task_ids))
            result.update(
                {
                    "processed": upload_result.get("processed", 0),
                    "uploaded": upload_result.get("uploaded", 0),
                    "failed": upload_result.get("failed", 0),
                }
            )
            return result

    def auto_collect_selected_devices(self, device_ids: list[int]) -> dict:
        if not device_ids:
            return {"device_count": 0, "metric_count": 0, "skipped_count": 0, "processed": 0, "uploaded": 0, "failed": 0}
        with SessionLocal() as db:
            devices = db.query(Device).filter(Device.id.in_(device_ids)).order_by(Device.sort_order.asc(), Device.id.asc()).all()
            before_ids = {
                row_id
                for (row_id,) in db.query(UploadTask.id)
                .filter(UploadTask.status == "pending")
                .all()
            }
            result = self._collect_devices(db, devices)
            new_task_ids = [
                row_id
                for (row_id,) in db.query(UploadTask.id)
                .filter(UploadTask.status == "pending")
                .order_by(UploadTask.id.asc())
                .all()
                if row_id not in before_ids
            ]
            upload_result = {"processed": 0, "uploaded": 0, "failed": 0}
            if new_task_ids:
                upload_result = upload_pending_records(db, task_ids=new_task_ids, max_tasks=len(new_task_ids))
            result.update(
                {
                    "processed": upload_result.get("processed", 0),
                    "uploaded": upload_result.get("uploaded", 0),
                    "failed": upload_result.get("failed", 0),
                }
            )
            return result

    def _collect_devices(self, db, devices: list[Device]) -> dict:
        success_count = 0
        total_metrics = 0
        skipped_count = 0
        save_interval_seconds = self._runtime_interval_seconds_from_db(db)
        for device in devices:
            metrics = (
                db.query(DeviceMetric)
                .filter(DeviceMetric.device_id == device.id)
                .order_by(DeviceMetric.sort_order.asc(), DeviceMetric.id.asc())
                .all()
            )
            config_status, _config_hint = self._device_config_summary(device, metrics)
            if config_status != "已完成":
                skipped_count += 1
                continue
            result = self._collect_once_for_interval(db, device, save_interval_seconds)
            device.status = "online"
            success_count += 1
            total_metrics += len(result.metrics)
        db.commit()
        return {"device_count": success_count, "metric_count": total_metrics, "skipped_count": skipped_count}

