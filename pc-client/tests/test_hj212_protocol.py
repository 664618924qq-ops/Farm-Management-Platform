from app.services.platform.hj212 import (
    HJ212Packet,
    build_hourly_packet,
    build_packet,
    build_realtime_packet,
    parse_packet,
    validate_data_ack,
)
from app.core.config import settings
from app.services.platform.rest_client import HJ212PlatformClient


def test_build_realtime_packet_uses_2011_payload_shape():
    packet = build_realtime_packet(
        {
            "collected_at": "2026-07-06T10:30:00",
            "metrics": [
                {"metric_code": "w01010", "metric_value": 28.6},
                {"metric_code": "w01014", "metric_value": 7.8},
            ],
        },
        mn="A110000_0001",
        qn="20260706103512345",
    )

    assert packet.length == "0157"
    assert packet.crc == "1980"
    assert "CN=2011" in packet.packet
    assert "DataTime=20260706103000" in packet.packet
    assert "w01010-Rtd=28.6,w01010-Flag=N" in packet.packet


def test_build_realtime_packet_carries_warning_quality_flag():
    packet = build_realtime_packet(
        {
            "collected_at": "2026-07-06T10:30:00",
            "metrics": [
                {"metric_code": "w01014", "metric_value": 2.5, "quality": "warning"},
            ],
        },
        mn="A110000_0001",
        qn="20260706103512345",
    )

    assert "w01014-Rtd=2.5,w01014-Flag=D" in packet.packet
    assert parse_packet(packet.packet)["CN"] == "2011"


def test_build_hourly_packet_uses_2061_payload_shape():
    packet = build_hourly_packet(
        {
            "collected_at": "2026-07-06T10:00:00",
            "metrics": [
                {"metric_code": "w01010", "metric_value": 28.4},
                {"metric_code": "w01014", "metric_value": 7.7},
            ],
        },
        mn="A110000_0001",
        qn="20260706103512345",
    )

    assert packet.length == "0157"
    assert packet.crc == "B681"
    assert "CN=2061" in packet.packet
    assert "DataTime=20260706100000" in packet.packet
    assert "w01010-Avg=28.4,w01010-Flag=N" in packet.packet
    assert packet.packet.endswith("B681\r\n")


def test_validate_data_ack_accepts_matching_9014_packet():
    ack_packet = "##0075QN=20260706103512345;ST=91;CN=9014;PW=123456;MN=A110000_0001;Flag=8;CP=&&&&0140\r\n"
    parsed = validate_data_ack(ack_packet, expected_qn="20260706103512345", expected_mn="A110000_0001")

    assert parsed["CN"] == "9014"
    assert parsed["QN"] == "20260706103512345"


def test_parse_packet_rejects_crc_mismatch():
    bad_packet = "##0075QN=20260706103512345;ST=91;CN=9014;PW=123456;MN=A110000_0001;Flag=8;CP=&&&&FFFF\r\n"

    try:
        parse_packet(bad_packet)
    except ValueError as exc:
        assert "CRC" in str(exc)
    else:
        raise AssertionError("expected CRC mismatch to fail")


def test_platform_client_reuses_long_connection(monkeypatch):
    HJ212PlatformClient().close()
    created_sockets = []

    class FakeSocket:
        def __init__(self):
            self.sent_packets: list[str] = []
            self.closed = False
            self.keepalive = []

        def sendall(self, payload: bytes) -> None:
            self.sent_packets.append(payload.decode("ascii"))

        def recv(self, _size: int) -> bytes:
            packet = parse_packet(self.sent_packets[-1])
            ack = build_packet(qn=packet["QN"], cn="9014", mn=packet["MN"], pw="123456", st="91", flag="8", cp="")
            return ack.packet.encode("ascii")

        def fileno(self) -> int:
            return 1

        def setsockopt(self, level, optname, value) -> None:
            self.keepalive.append((level, optname, value))

        def setblocking(self, flag: bool) -> None:
            return None

        def close(self) -> None:
            self.closed = True

    def fake_create_connection(_addr, timeout):
        sock = FakeSocket()
        created_sockets.append((sock, timeout))
        return sock

    packets = [
        build_packet(qn="20260706103512345", cn="2011", mn="A110000_0001", pw="123456", cp="DataTime=20260706103000"),
        build_packet(qn="20260706103512346", cn="2011", mn="A110000_0001", pw="123456", cp="DataTime=20260706103100"),
    ]

    client = HJ212PlatformClient()
    second_client = HJ212PlatformClient()
    monkeypatch.setattr("app.services.platform.rest_client.socket.create_connection", fake_create_connection)
    monkeypatch.setattr("app.services.platform.rest_client.select.select", lambda r, w, x, timeout: (r, [], []))
    monkeypatch.setattr(client, "_build_packet", lambda payload, command_code: packets.pop(0))
    monkeypatch.setattr(second_client, "_build_packet", lambda payload, command_code: packets.pop(0))
    monkeypatch.setattr(settings, "gateway_code", "A110000_0001")

    first = client.upload_payload({"collected_at": "2026-07-06T10:30:00", "metrics": [{"metric_code": "w01010", "metric_value": 0}]}, command_code="2011")
    second = second_client.upload_payload({"collected_at": "2026-07-06T10:31:00", "metrics": [{"metric_code": "w01010", "metric_value": 0}]}, command_code="2011")

    assert first["success"] is True
    assert second["success"] is True
    assert len(created_sockets) == 1
    assert len(created_sockets[0][0].sent_packets) == 2


def test_platform_client_requires_9014_ack(monkeypatch):
    HJ212PlatformClient().close()
    created_sockets = []

    class FakeSocket:
        def __init__(self):
            self.sent_packets: list[str] = []
            self.closed = False

        def fileno(self) -> int:
            return 1

        def sendall(self, payload: bytes) -> None:
            self.sent_packets.append(payload.decode("ascii"))

        def setsockopt(self, level, optname, value) -> None:
            return None

        def setblocking(self, flag: bool) -> None:
            return None

        def close(self) -> None:
            self.closed = True

    def fake_create_connection(_addr, timeout):
        sock = FakeSocket()
        created_sockets.append(sock)
        return sock

    select_timeouts = []

    def fake_select(r, w, x, timeout):
        select_timeouts.append(timeout)
        return ([], [], [])

    client = HJ212PlatformClient()
    monkeypatch.setattr("app.services.platform.rest_client.socket.create_connection", fake_create_connection)
    monkeypatch.setattr("app.services.platform.rest_client.select.select", fake_select)
    monkeypatch.setattr(settings, "platform_ack_timeout_seconds", 3.0)
    monkeypatch.setattr(
        client,
        "_build_packet",
        lambda payload, command_code: build_packet(qn="20260706103512345", cn="2011", mn="A110000_0001", pw="123456", cp="DataTime=20260706103000"),
    )

    result = client.upload_payload({"metrics": []}, command_code="2011")

    assert result["success"] is False
    assert "连接成功但未收到 ACK" in result["error"]
    assert "3 秒" in result["error"]
    assert select_timeouts == [3.0]
    assert created_sockets[0].closed is True
    status = HJ212PlatformClient.get_runtime_status()
    assert status["connection_status"] == "disconnected"
    assert status["ack_received"] is False
    assert "CN=2011" in status["last_packet"]


def test_platform_client_reports_connection_failure(monkeypatch):
    HJ212PlatformClient().close()
    client = HJ212PlatformClient()
    monkeypatch.setattr(settings, "platform_host", "127.0.0.1")
    monkeypatch.setattr(settings, "platform_port", 9100)
    monkeypatch.setattr("app.services.platform.rest_client.socket.create_connection", lambda *args, **kwargs: (_ for _ in ()).throw(ConnectionRefusedError("refused")))

    result = client.upload_payload({"collected_at": "2026-07-06T10:30:00", "metrics": [{"metric_code": "w01010", "metric_value": 0}]}, command_code="2011")

    assert result["success"] is False
    assert "未连接到 127.0.0.1:9100" in result["error"]


def test_platform_client_reports_non_9014_ack(monkeypatch):
    HJ212PlatformClient().close()

    class FakeSocket:
        def sendall(self, _payload: bytes) -> None:
            return None

        def recv(self, _size: int) -> bytes:
            return build_packet(qn="20260706103512345", cn="9999", mn="A110000_0001", pw="123456", st="91", flag="8", cp="").packet.encode("ascii")

        def fileno(self) -> int:
            return 1

        def setsockopt(self, level, optname, value) -> None:
            return None

        def setblocking(self, flag: bool) -> None:
            return None

        def close(self) -> None:
            return None

    client = HJ212PlatformClient()
    monkeypatch.setattr("app.services.platform.rest_client.socket.create_connection", lambda *args, **kwargs: FakeSocket())
    monkeypatch.setattr("app.services.platform.rest_client.select.select", lambda r, w, x, timeout: (r, [], []))
    monkeypatch.setattr(settings, "gateway_code", "A110000_0001")
    monkeypatch.setattr(
        client,
        "_build_packet",
        lambda payload, command_code: build_packet(qn="20260706103512345", cn="2011", mn="A110000_0001", pw="123456", cp="DataTime=20260706103000"),
    )

    result = client.upload_payload({"metrics": []}, command_code="2011")

    assert result["success"] is False
    assert "收到 ACK 但不是 CN=9014" in result["error"]


def test_platform_client_reports_platform_error_response(monkeypatch):
    HJ212PlatformClient().close()

    class FakeSocket:
        def sendall(self, _payload: bytes) -> None:
            return None

        def recv(self, _size: int) -> bytes:
            return b"ERROR: parse failed\n"

        def fileno(self) -> int:
            return 1

        def setsockopt(self, level, optname, value) -> None:
            return None

        def setblocking(self, flag: bool) -> None:
            return None

        def close(self) -> None:
            return None

    client = HJ212PlatformClient()
    monkeypatch.setattr("app.services.platform.rest_client.socket.create_connection", lambda *args, **kwargs: FakeSocket())
    monkeypatch.setattr("app.services.platform.rest_client.select.select", lambda r, w, x, timeout: (r, [], []))
    monkeypatch.setattr(
        client,
        "_build_packet",
        lambda payload, command_code: build_packet(qn="20260706103512345", cn="2011", mn="A110000_0001", pw="123456", cp="DataTime=20260706103000"),
    )

    result = client.upload_payload({"metrics": []}, command_code="2011")

    assert result["success"] is False
    assert "平台返回 ERROR" in result["error"]
