from app.services.telemetry_ingestion import normalize_payload


def test_normalize_payload_returns_device_and_metrics() -> None:
    payload = {
        "farmCode": "FARM-001",
        "shedCode": "SHED-001",
        "deviceCode": "DEV-001",
        "reportedAt": "2026-07-06T10:00:00+08:00",
        "metrics": [{"code": "temperature", "value": 28.5, "unit": "C"}],
    }

    normalized = normalize_payload(payload)

    assert normalized.device_code == "DEV-001"
    assert normalized.metrics[0].code == "temperature"
