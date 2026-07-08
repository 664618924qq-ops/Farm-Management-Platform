import socket
import select
from datetime import datetime

from app.core.config import settings
from app.services.platform.base import PlatformClient
from app.services.platform.hj212 import (
    HJ212Packet,
    HJ212ProtocolError,
    build_hourly_packet,
    build_realtime_packet,
    validate_data_ack,
)


class HJ212PlatformClient(PlatformClient):
    _shared_sock: socket.socket | None = None
    _shared_endpoint: tuple[str, int] | None = None
    _connection_status: str = "disconnected"
    _last_send_time: str = ""
    _last_send_result: str = ""
    _last_response: str = ""
    _last_ack_received: bool | None = None
    _last_packet: str = ""
    _last_error: str = ""

    def __init__(self) -> None:
        pass

    @classmethod
    def get_runtime_status(cls) -> dict:
        endpoint = ""
        if cls._shared_endpoint is not None:
            endpoint = f"{cls._shared_endpoint[0]}:{cls._shared_endpoint[1]}"
        return {
            "connection_status": cls._connection_status,
            "last_send_time": cls._last_send_time,
            "last_send_result": cls._last_send_result,
            "ack_received": cls._last_ack_received,
            "last_response": cls._last_response,
            "last_packet": cls._last_packet,
            "last_error": cls._last_error,
            "endpoint": endpoint,
        }

    @classmethod
    def _stamp_send_time(cls) -> str:
        cls._last_send_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return cls._last_send_time

    def _fail(self, message: str, *, response: str = "") -> dict:
        self.__class__._stamp_send_time()
        self.__class__._last_send_result = "failed"
        self.__class__._last_response = response
        self.__class__._last_ack_received = False
        self.__class__._last_error = message
        self.close()
        return {"success": False, "error": message, "packet": self.__class__._last_packet}

    def _build_packet(self, payload: dict, command_code: str) -> HJ212Packet:
        mn = settings.gateway_code.strip()
        if not mn:
            raise HJ212ProtocolError("gateway code is required")
        if command_code == "2011":
            return build_realtime_packet(payload, mn=mn)
        if command_code == "2061":
            return build_hourly_packet(payload, mn=mn)
        raise HJ212ProtocolError(f"unsupported command code: {command_code}")

    def _endpoint_address(self) -> tuple[str, int]:
        return (settings.platform_host, settings.platform_port)

    def _connect(self) -> socket.socket:
        endpoint = self._endpoint_address()
        if self.__class__._shared_sock is not None and self.__class__._shared_endpoint == endpoint:
            self.__class__._connection_status = "connected"
            return self.__class__._shared_sock
        self.close()
        sock = socket.create_connection(endpoint, timeout=5.0)
        sock.setblocking(False)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.__class__._shared_sock = sock
        self.__class__._shared_endpoint = endpoint
        self.__class__._connection_status = "connected"
        return self.__class__._shared_sock

    def close(self) -> None:
        if self.__class__._shared_sock is not None:
            try:
                self.__class__._shared_sock.close()
            finally:
                self.__class__._shared_sock = None
                self.__class__._shared_endpoint = None
        self.__class__._connection_status = "disconnected"

    def upload_payload(self, payload: dict, *, command_code: str) -> dict:
        try:
            packet = self._build_packet(payload, command_code)
            self.__class__._last_packet = packet.packet
            self.__class__._last_error = ""
            try:
                sock = self._connect()
            except OSError as exc:
                host, port = self._endpoint_address()
                return self._fail(f"未连接到 {host}:{port}：{exc}")
            sock.sendall(packet.packet.encode("ascii"))
            self.__class__._stamp_send_time()
            ack_timeout = max(float(settings.platform_ack_timeout_seconds), 0.1)
            readable, _, _ = select.select([sock], [], [], ack_timeout)
            if not readable:
                return self._fail(f"连接成功但未收到 ACK（等待 {ack_timeout:g} 秒）")
            response = sock.recv(4096)
            if not response:
                return self._fail("平台关闭连接，未返回 9014 ACK")
            decoded = response.decode("ascii", errors="ignore")
            if decoded.strip().startswith("ERROR"):
                return self._fail(f"平台返回 ERROR：{decoded.strip()}", response=decoded.strip())
            try:
                validate_data_ack(decoded, expected_qn=packet.qn, expected_mn=settings.gateway_code.strip())
            except HJ212ProtocolError as exc:
                if "unexpected ack command" in str(exc):
                    return self._fail(f"收到 ACK 但不是 CN=9014：{decoded.strip()}", response=decoded.strip())
                return self._fail(f"收到 ACK 但校验失败：{exc}", response=decoded.strip())
            self.__class__._last_send_result = "ack"
            self.__class__._last_response = decoded.strip()
            self.__class__._last_ack_received = True
            return {"success": True, "response": decoded.strip(), "packet": packet.packet}
        except Exception as exc:
            return self._fail(f"发送异常：{exc}")

    def upload_telemetry(self, payload: dict) -> dict:
        return self.upload_payload(payload, command_code="2011")


RestPlatformClient = HJ212PlatformClient
