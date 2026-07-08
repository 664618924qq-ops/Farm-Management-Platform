from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


class HJ212ProtocolError(ValueError):
    pass


@dataclass(frozen=True)
class HJ212Packet:
    qn: str
    cn: str
    data: str
    length: str
    crc: str
    packet: str


def format_qn(source: datetime | None = None) -> str:
    moment = source or datetime.now()
    return moment.strftime("%Y%m%d%H%M%S%f")[:17]


def format_data_time(value: str | datetime) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y%m%d%H%M%S")
    normalized = value.strip()
    if not normalized:
        raise HJ212ProtocolError("collected_at is required")
    if "T" in normalized:
        normalized = normalized.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).strftime("%Y%m%d%H%M%S")
    if len(normalized) == 14 and normalized.isdigit():
        return normalized
    raise HJ212ProtocolError(f"unsupported datetime format: {value}")


def crc16(text: str) -> str:
    crc_reg = 0xFFFF
    for byte in text.encode("ascii"):
        crc_reg = (crc_reg >> 8) ^ byte
        for _ in range(8):
            check = crc_reg & 0x0001
            crc_reg >>= 1
            if check == 0x0001:
                crc_reg ^= 0xA001
    return f"{crc_reg:04X}"


def _normalize_metric_value(value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise HJ212ProtocolError("metric_value is required")
    return text


def _metric_flag(metric: dict) -> str:
    quality = str(metric.get("quality") or metric.get("analysis_status") or "").strip().lower()
    if quality and quality not in {"good", "normal", "n"}:
        return "D"
    return "N"


def _build_cp_payload(payload: dict, *, suffix: str) -> str:
    collected_at = payload.get("collected_at") or payload.get("hour_bucket")
    if not collected_at:
        raise HJ212ProtocolError("payload missing collected_at")
    metrics = payload.get("metrics") or []
    if not metrics:
        raise HJ212ProtocolError("payload metrics are empty")

    items = [f"DataTime={format_data_time(collected_at)}"]
    for metric in metrics:
        metric_code = str(metric.get("metric_code", "")).strip()
        if not metric_code:
            raise HJ212ProtocolError("metric_code is required")
        metric_value = _normalize_metric_value(metric.get("metric_value"))
        items.append(f"{metric_code}-{suffix}={metric_value},{metric_code}-Flag={_metric_flag(metric)}")
    return ";".join(items)


def build_packet(*, qn: str, cn: str, mn: str, pw: str, cp: str, st: str = "21", flag: str = "9") -> HJ212Packet:
    data = f"QN={qn};ST={st};CN={cn};PW={pw};MN={mn};Flag={flag};CP=&&{cp}&&"
    length = f"{len(data):04d}"
    data_crc = crc16(data)
    packet = f"##{length}{data}{data_crc}\r\n"
    return HJ212Packet(qn=qn, cn=cn, data=data, length=length, crc=data_crc, packet=packet)


def build_realtime_packet(payload: dict, *, mn: str, pw: str = "123456", qn: str | None = None) -> HJ212Packet:
    return build_packet(qn=qn or format_qn(), cn="2011", mn=mn, pw=pw, cp=_build_cp_payload(payload, suffix="Rtd"))


def build_hourly_packet(payload: dict, *, mn: str, pw: str = "123456", qn: str | None = None) -> HJ212Packet:
    return build_packet(qn=qn or format_qn(), cn="2061", mn=mn, pw=pw, cp=_build_cp_payload(payload, suffix="Avg"))


def parse_packet(packet: str) -> dict[str, str]:
    text = packet.strip("\r\n")
    if not text.startswith("##"):
        raise HJ212ProtocolError("packet missing header")
    if len(text) < 10:
        raise HJ212ProtocolError("packet too short")

    length_text = text[2:6]
    if not length_text.isdigit():
        raise HJ212ProtocolError("packet length is invalid")
    data_length = int(length_text)
    data = text[6 : 6 + data_length]
    crc_text = text[6 + data_length : 10 + data_length]
    if len(data) != data_length or len(crc_text) != 4:
        raise HJ212ProtocolError("packet length does not match payload")
    if crc16(data) != crc_text.upper():
        raise HJ212ProtocolError("packet CRC mismatch")

    result: dict[str, str] = {"raw": text, "length": length_text, "data": data, "crc": crc_text.upper()}
    cp_start = data.find("CP=&&")
    cp_end = data.rfind("&&")
    prefix = data
    if cp_start >= 0 and cp_end > cp_start:
        prefix = data[:cp_start]
        result["CP"] = data[cp_start + 5 : cp_end]
    for part in prefix.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        result[key] = value
    return result


def validate_data_ack(packet: str, *, expected_qn: str, expected_mn: str) -> dict[str, str]:
    parsed = parse_packet(packet)
    if parsed.get("CN") != "9014":
        raise HJ212ProtocolError(f"unexpected ack command: {parsed.get('CN')}")
    if parsed.get("QN") != expected_qn:
        raise HJ212ProtocolError(f"unexpected ack qn: {parsed.get('QN')}")
    if parsed.get("MN") != expected_mn:
        raise HJ212ProtocolError(f"unexpected ack mn: {parsed.get('MN')}")
    return parsed
