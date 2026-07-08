from __future__ import annotations

from app.services.hj212 import build_packet
from test_protocol_upload import RAW_PACKET

HOURLY_PACKET = build_packet(
    "QN=20260706103512345;ST=21;CN=2061;PW=123456;MN=A110000_0001;Flag=9;CP=&&"
    "DataTime=20260706100000;w01010-Avg=28.4,w01010-Flag=N;w01014-Avg=10.1,w01014-Flag=N;"
    "w01001-Avg=6.6,w01001-Flag=N;w01017-Avg=15.0,w01017-Flag=N;w01019-Avg=1.022,w01019-Flag=N&&"
)

HOURLY_PACKET_ANALYSIS = build_packet(
    "QN=20260706104512345;ST=21;CN=2061;PW=123456;MN=A110000_ANALYSIS;Flag=9;CP=&&"
    "DataTime=20260706100000;w01014-Avg=10.1,w01014-Flag=N&&"
)


def test_query_data_filters_database_history_by_cn_and_mn(client) -> None:
    client.post("/api/v1/protocol/upload", content=RAW_PACKET, headers={"Content-Type": "text/plain; charset=utf-8"})
    client.post("/api/v1/protocol/upload", content=HOURLY_PACKET, headers={"Content-Type": "text/plain; charset=utf-8"})

    response = client.get("/api/v1/data/query", params={"cn": "2061", "mn": "A110000_0001", "sensorCode": "w01014"})

    data = response.json()
    assert response.status_code == 200
    assert data["dataSource"] == "database"
    assert data["mode"] == "小时数据查询"
    assert data["timeSemantics"] == "监测时段/小时统计"
    assert len(data["items"]) == 1
    assert data["items"][0]["commandCode"] == "2061"
    assert data["items"][0]["recordedAtBeijing"] == "2026-07-06T10:00:00+08:00"
    assert data["items"][0]["qualityLabel"] == "超标"
    assert "地表水技术要求目录" in data["items"][0]["qualityBasis"]


def test_query_data_accepts_multiple_sensor_codes(client) -> None:
    client.post("/api/v1/protocol/upload", content=HOURLY_PACKET, headers={"Content-Type": "text/plain; charset=utf-8"})

    response = client.get(
        "/api/v1/data/query",
        params={"cn": "2061", "mn": "A110000_0001", "sensorCode": "w01010,w01014"},
    )

    data = response.json()
    assert response.status_code == 200
    assert {item["sensorCode"] for item in data["items"]} == {"w01010", "w01014"}


def test_analysis_uses_database_records_and_creates_quality_alert_record(client) -> None:
    client.post("/api/v1/protocol/upload", content=HOURLY_PACKET_ANALYSIS, headers={"Content-Type": "text/plain; charset=utf-8"})

    response = client.get("/api/v1/data/analysis", params={"cn": "2061", "mn": "A110000_ANALYSIS", "sensorCode": "w01014"})
    data = response.json()

    assert response.status_code == 200
    assert data["dataSource"] == "database"
    assert data["summary"]["recordCount"] == 1
    assert data["summary"]["findingCount"] == 1
    assert data["findings"][0]["qualityLabel"] == "超标"
    assert "地表水技术要求目录" in data["findings"][0]["basis"]


def test_sms_test_is_dry_run_and_records_reserved_log(client) -> None:
    response = client.post(
        "/api/v1/notifications/sms-test",
        json={"phoneNumber": "13800000000", "templateCode": "quality_alert", "content": "测试"},
    )

    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "dry_run"
    assert "不会产生资费" in data["message"]
    assert data["logId"] > 0
