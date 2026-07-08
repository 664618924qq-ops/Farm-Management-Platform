RAW_PACKET = "##0247QN=20260706103512345;ST=21;CN=2011;PW=123456;MN=A110000_0001;Flag=9;CP=&&DataTime=20260706103000;w01010-Rtd=28.6,w01010-Flag=N;w01014-Rtd=7.8,w01014-Flag=N;w01001-Rtd=6.5,w01001-Flag=N;w01017-Rtd=15.2,w01017-Flag=N;w01019-Rtd=1.023,w01019-Flag=N&&1540\r\n"
BAD_PACKET = "##0012QN=1;CN=2011FFFF\r\n"


def test_protocol_upload_accepts_raw_hj212_packet(client) -> None:
    response = client.post(
        "/api/v1/protocol/upload",
        content=RAW_PACKET,
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )

    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "accepted"
    assert data["cn"] == "2011"
    assert data["metricCount"] == 5


def test_protocol_logs_show_uploaded_packet(client) -> None:
    client.post(
        "/api/v1/protocol/upload",
        content=RAW_PACKET,
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )

    response = client.get("/api/v1/protocol/logs")

    data = response.json()
    assert response.status_code == 200
    assert data[0]["mn"] == "A110000_0001"
    assert data[0]["cn"] == "2011"
    assert data[0]["status"] == "accepted"
    assert data[0]["metricCount"] == 5
    assert data[0]["rawPacket"].startswith("##0247QN=")
    assert data[0]["dataTime"] == "2026-07-06T10:30:00"
    assert data[0]["ackPacket"].startswith("##")


def test_protocol_logs_show_rejected_packet(client) -> None:
    response = client.post(
        "/api/v1/protocol/upload",
        content=BAD_PACKET,
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )

    logs = client.get("/api/v1/protocol/logs").json()
    assert response.status_code == 400
    assert logs[0]["status"] == "rejected"
    assert logs[0]["errorMessage"] is not None


def test_protocol_logs_show_ingest_failed_status(client, monkeypatch) -> None:
    from app.api.routes import protocol as protocol_route

    def broken_ingest(*args, **kwargs):
        raise RuntimeError("forced ingest failure")

    monkeypatch.setattr(protocol_route, "ingest_payload", broken_ingest)

    response = client.post(
        "/api/v1/protocol/upload",
        content=RAW_PACKET,
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )

    logs = client.get("/api/v1/protocol/logs").json()
    assert response.status_code == 500
    assert logs[0]["status"] == "ingest_failed"
    assert logs[0]["mn"] == "A110000_0001"
    assert logs[0]["cn"] == "2011"
    assert logs[0]["errorMessage"] == "forced ingest failure"
