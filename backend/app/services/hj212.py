from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class HJ212Metric:
    code: str
    value_key: str
    value: float
    flag: str


@dataclass(slots=True)
class HJ212Message:
    qn: str
    st: str
    cn: str
    pw: str
    mn: str
    flag: str
    data_time: datetime
    metrics: list[HJ212Metric]
    body: str
    length: int
    crc: str


def compute_crc16(data: str) -> str:
    crc_reg = 0xFFFF
    for byte in data.encode("ascii"):
        crc_reg = (crc_reg >> 8) ^ byte
        for _ in range(8):
            check = crc_reg & 0x0001
            crc_reg >>= 1
            if check == 0x0001:
                crc_reg ^= 0xA001
    return f"{crc_reg:04X}"


def _split_packet(raw_packet: str) -> tuple[str, int, str]:
    cleaned = raw_packet.strip()
    if not cleaned.startswith("##"):
        raise ValueError("Invalid packet header")
    if len(cleaned) < 10:
        raise ValueError("Packet too short")
    length = int(cleaned[2:6])
    body = cleaned[6 : 6 + length]
    crc = cleaned[6 + length : 10 + length]
    return body, length, crc


def _parse_cp(cp_content: str) -> tuple[datetime, list[HJ212Metric]]:
    segments = [segment for segment in cp_content.split(";") if segment]
    data_time_raw = next((item.split("=", 1)[1] for item in segments if item.startswith("DataTime=")), None)
    if data_time_raw is None:
        raise ValueError("Missing DataTime in CP section")

    grouped: dict[str, dict[str, str]] = {}
    for segment in segments[1:]:
        parts = [part for part in segment.split(",") if part]
        for part in parts:
            key, value = part.split("=", 1)
            base_code, suffix = key.split("-", 1)
            grouped.setdefault(base_code, {})[suffix] = value

    metrics: list[HJ212Metric] = []
    for code, values in grouped.items():
        value_key = "Rtd" if "Rtd" in values else "Avg" if "Avg" in values else None
        if value_key is None:
            continue
        metrics.append(
            HJ212Metric(
                code=code,
                value_key=value_key,
                value=float(values[value_key]),
                flag=values.get("Flag", "N"),
            )
        )

    return datetime.strptime(data_time_raw, "%Y%m%d%H%M%S"), metrics


def parse_message(raw_packet: str) -> HJ212Message:
    body, length, crc = _split_packet(raw_packet)
    calculated_crc = compute_crc16(body)
    if calculated_crc.upper() != crc.upper():
        raise ValueError(f"CRC mismatch: expected {crc}, calculated {calculated_crc}")

    cp_start = body.find("CP=&&")
    cp_end = body.rfind("&&")
    if cp_start == -1 or cp_end == -1 or cp_end <= cp_start + 5:
        raise ValueError("Invalid CP section")

    head_part = body[:cp_start].rstrip(";")
    cp_content = body[cp_start + 5 : cp_end]
    head_fields = {}
    for item in head_part.split(";"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        head_fields[key] = value

    data_time, metrics = _parse_cp(cp_content)
    return HJ212Message(
        qn=head_fields["QN"],
        st=head_fields["ST"],
        cn=head_fields["CN"],
        pw=head_fields["PW"],
        mn=head_fields["MN"],
        flag=head_fields.get("Flag", "8"),
        data_time=data_time,
        metrics=metrics,
        body=body,
        length=length,
        crc=crc,
    )


def build_packet(body: str) -> str:
    body_length = len(body)
    crc = compute_crc16(body)
    return f"##{body_length:04d}{body}{crc}\r\n"


def build_data_ack(message: HJ212Message) -> str:
    body = f"QN={message.qn};ST=91;CN=9014;PW={message.pw};MN={message.mn};Flag=8;CP=&&&&"
    return build_packet(body)
