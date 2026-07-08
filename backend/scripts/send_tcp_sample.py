from __future__ import annotations

import json
import socket
from datetime import datetime

HOST = "127.0.0.1"
PORT = 9100

payload = {
    "farmCode": "FARM-001",
    "shedCode": "SHED-001",
    "deviceCode": "DEV-001",
    "reportedAt": datetime.now().astimezone().isoformat(),
    "metrics": [
        {"code": "temperature", "value": 29.1, "unit": "C"},
        {"code": "humidity", "value": 73.2, "unit": "%"},
        {"code": "ammonia", "value": 11.8, "unit": "ppm"},
        {"code": "co2", "value": 840.0, "unit": "ppm"},
        {"code": "illumination", "value": 280.0, "unit": "lx"},
    ],
}


def main() -> None:
    with socket.create_connection((HOST, PORT), timeout=10) as sock:
        sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        response = sock.recv(4096).decode("utf-8").strip()
        print(response)


if __name__ == "__main__":
    main()
