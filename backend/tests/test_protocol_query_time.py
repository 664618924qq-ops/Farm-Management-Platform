from __future__ import annotations

import uuid
from datetime import datetime

from app.services.hj212 import build_packet
from app.services.timezone import BEIJING_TZ


def packet_for(
    cn: str,
    *,
    qn: str,
    data_time: str,
    mn: str = "A110000_0001",
    value_key: str = "Rtd",
) -> str:
    body = (
        f"QN={qn};ST=21;CN={cn};PW=123456;MN={mn};Flag=9;"
        f"CP=&&DataTime={data_time};w01010-{value_key}=28.6,w01010-Flag=N&&"
    )
    return build_packet(body)


def upload_packet(client, raw_packet: str) -> None:
    response = client.post(
        "/api/v1/protocol/upload",
        content=raw_packet,
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    assert response.status_code == 200


def test_protocol_logs_can_query_persisted_cn_2011_and_2061_history(client) -> None:
    upload_packet(
        client,
        packet_for(
            "2011",
            qn="20260706103512345",
            data_time="20260706103000",
            mn="QA_QUERY_2011",
            value_key="Rtd",
        ),
    )
    upload_packet(
        client,
        packet_for(
            "2061",
            qn="20260706110012345",
            data_time="20260706110000",
            mn="QA_QUERY_2061",
            value_key="Avg",
        ),
    )

    cn2011 = client.get("/api/v1/protocol/logs", params={"cn": "2011", "mn": "QA_QUERY_2011"}).json()
    cn2061 = client.get("/api/v1/protocol/logs", params={"cn": "2061", "mn": "QA_QUERY_2061"}).json()

    assert [row["cn"] for row in cn2011] == ["2011"]
    assert [row["cn"] for row in cn2061] == ["2061"]
    assert cn2011[0]["mn"] == "QA_QUERY_2011"
    assert cn2011[0]["dataTime"] == "2026-07-06T10:30:00"
    assert cn2061[0]["dataTime"] == "2026-07-06T11:00:00"
    assert cn2011[0]["rawPacket"].startswith("##")
    assert "CN=9014" in cn2011[0]["ackPacket"]


def test_protocol_logs_can_query_multiple_cn_values(client) -> None:
    mn = f"QA_MULTI_CN_{uuid.uuid4().hex}"
    upload_packet(
        client,
        packet_for(
            "2011",
            qn="20260706120112345",
            data_time="20260706120100",
            mn=mn,
            value_key="Rtd",
        ),
    )
    upload_packet(
        client,
        packet_for(
            "2061",
            qn="20260706120212345",
            data_time="20260706120000",
            mn=mn,
            value_key="Avg",
        ),
    )

    comma_response = client.get("/api/v1/protocol/logs", params={"cn": "2011,2061", "mn": mn})
    repeated_response = client.get(
        "/api/v1/protocol/logs",
        params=[("cn", "2011"), ("cn", "2061"), ("mn", mn)],
    )

    assert comma_response.status_code == 200
    assert repeated_response.status_code == 200
    assert {row["cn"] for row in comma_response.json()} == {"2011", "2061"}
    assert {row["cn"] for row in repeated_response.json()} == {"2011", "2061"}


def test_protocol_logs_support_empty_cn_as_all_and_time_range(client) -> None:
    from app.db.session import SessionLocal
    from app.models.protocol import ProtocolUploadLog

    mn = f"QA_MULTI_CN_RANGE_{uuid.uuid4().hex}"
    upload_packet(
        client,
        packet_for("2011", qn="20260706100012345", data_time="20260706100000", mn=mn, value_key="Rtd"),
    )
    upload_packet(
        client,
        packet_for("2061", qn="20260706110012345", data_time="20260706110000", mn=mn, value_key="Avg"),
    )
    with SessionLocal() as db:
        logs = db.query(ProtocolUploadLog).filter(ProtocolUploadLog.mn == mn).all()
        for log in logs:
            log.received_at = datetime(2026, 7, 6, 10, 0, 0) if log.cn == "2011" else datetime(2026, 7, 6, 11, 0, 0)
        db.commit()

    only_2011 = client.get("/api/v1/protocol/logs", params={"cn": "2011", "mn": mn}).json()
    only_2061 = client.get("/api/v1/protocol/logs", params={"cn": "2061", "mn": mn}).json()
    both = client.get("/api/v1/protocol/logs", params={"cn": "2011,2061", "mn": mn}).json()
    empty_all = client.get("/api/v1/protocol/logs", params={"mn": mn}).json()
    time_filtered = client.get(
        "/api/v1/protocol/logs",
        params={
            "mn": mn,
            "startTime": "2026-07-06T10:30:00",
            "endTime": "2026-07-06T11:30:00",
        },
    ).json()

    assert [row["cn"] for row in only_2011] == ["2011"]
    assert [row["cn"] for row in only_2061] == ["2061"]
    assert [row["cn"] for row in both] == ["2061", "2011"]
    assert [row["cn"] for row in empty_all] == ["2061", "2011"]
    assert [row["cn"] for row in time_filtered] == ["2061"]


def test_protocol_logs_reject_end_time_before_start_time(client) -> None:
    response = client.get(
        "/api/v1/protocol/logs",
        params={
            "startTime": "2026-07-06T11:00:00",
            "endTime": "2026-07-06T10:00:00",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "结束时间不能早于开始时间"


def test_protocol_received_at_is_beijing_time_without_large_clock_drift(client) -> None:
    upload_packet(
        client,
        packet_for("2011", qn="20260706103512345", data_time="20260706103000", value_key="Rtd"),
    )

    row = client.get("/api/v1/protocol/logs", params={"cn": "2011"}).json()[0]

    received_at = datetime.fromisoformat(row["receivedAt"])
    now_beijing = datetime.now(BEIJING_TZ)
    assert row["dataTime"] == "2026-07-06T10:30:00"
    assert received_at.utcoffset().total_seconds() == 8 * 60 * 60
    assert abs((now_beijing - received_at).total_seconds()) < 300
