def test_dashboard_summary_returns_expected_keys(client) -> None:
    response = client.get("/api/v1/dashboard/summary")

    data = response.json()
    assert response.status_code == 200
    assert "farmCount" in data
    assert "shedCount" in data
    assert "onlineDeviceCount" in data
    assert "activeAlertCount" in data
    assert "integrationStatus" in data
    assert "lastPacketTime" in data["integrationStatus"]
    assert "lastDevice" in data["integrationStatus"]


def test_dashboard_summary_returns_latest_protocol_status(client) -> None:
    packet = "##0247QN=20260706103512345;ST=21;CN=2011;PW=123456;MN=A110000_0001;Flag=9;CP=&&DataTime=20260706103000;w01010-Rtd=28.6,w01010-Flag=N;w01014-Rtd=7.8,w01014-Flag=N;w01001-Rtd=6.5,w01001-Flag=N;w01017-Rtd=15.2,w01017-Flag=N;w01019-Rtd=1.023,w01019-Flag=N&&1540\r\n"
    client.post(
        "/api/v1/protocol/upload",
        content=packet,
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )

    response = client.get("/api/v1/dashboard/summary")

    data = response.json()
    assert response.status_code == 200
    assert data["integrationStatus"]["lastDevice"] == "A110000_0001"
    assert data["integrationStatus"]["lastStatus"] == "accepted"
    assert data["integrationStatus"]["lastCommand"] == "2011"
    assert data["integrationStatus"]["lastMetricCount"] == 5
    assert data["integrationStatus"]["lastReceiveResult"] == "HTTP accepted and stored"
    assert data["integrationStatus"]["lastAckStatus"] == "valid_9014_ack"
    assert data["integrationStatus"]["lastAckSummary"] == "CN=9014 ACK returned"
