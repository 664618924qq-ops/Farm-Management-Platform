from __future__ import annotations


def normalize_metric_fields(metric_code: str, metric_name: str, metric_unit: str | None) -> tuple[str, str, str | None]:
    code = (metric_code or "").strip()
    name = (metric_name or "").strip()
    unit = (metric_unit or "").strip() or None

    normalized_name = name.lower()
    normalized_code = code.lower()

    if normalized_name in {"水温", "watertemp", "water_temp"} or normalized_code == "water_temp":
        return "w01010", "水温", "℃"
    if normalized_name == "ph" or normalized_code == "ph":
        return "w01001", "pH", "无量纲"
    if normalized_name in {"溶解氧", "do"} or normalized_code in {"do", "w01009"}:
        return "w01014", "溶解氧", "mg/L"
    if normalized_name in {"盐度", "salinity"} or normalized_code in {"salinity", "w01012"}:
        return "w01017", "盐度", "‰"
    if normalized_name in {"电导率", "conductivity"} or normalized_code in {"conductivity", "w01019"}:
        return "w01019", "电导率", "uS/cm"
    return code, name, unit


def normalize_metric_payload(payload: dict) -> dict:
    metrics = []
    for item in payload.get("metrics", []):
        code, name, unit = normalize_metric_fields(
            str(item.get("metric_code", "")),
            str(item.get("metric_name", "")),
            item.get("metric_unit"),
        )
        normalized = dict(item)
        normalized["metric_code"] = code
        normalized["metric_name"] = name
        normalized["metric_unit"] = unit
        metrics.append(normalized)
    normalized_payload = dict(payload)
    normalized_payload["metrics"] = metrics
    return normalized_payload
