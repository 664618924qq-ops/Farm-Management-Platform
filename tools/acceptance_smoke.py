from __future__ import annotations

import argparse
import json
import os
import socket
import urllib.error
import urllib.request
import uuid
from pathlib import Path


REALTIME_PACKET = (
    "##0247QN=20260706103512345;ST=21;CN=2011;PW=123456;MN=A110000_0001;Flag=9;"
    "CP=&&DataTime=20260706103000;w01010-Rtd=28.6,w01010-Flag=N;w01014-Rtd=7.8,"
    "w01014-Flag=N;w01001-Rtd=6.5,w01001-Flag=N;w01017-Rtd=15.2,w01017-Flag=N;"
    "w01019-Rtd=1.023,w01019-Flag=N&&1540\r\n"
)
BROKEN_PACKET = "##0012QN=1;CN=2011FFFF\r\n"
FINAL_HOST = "127.0.0.1"
FINAL_PORT = 9100
ACK_POLICY = "required"
KNOWN_FAILURE_CATEGORIES = ["acknowledgement", "connection", "protocol", "ui evidence"]


def failure_result(
    category: str,
    reason: str,
    *,
    host: str = FINAL_HOST,
    port: int = FINAL_PORT,
    **extra: object,
) -> dict:
    return {
        "status": "failed",
        "failureCategory": category,
        "failureReason": reason,
        "endpoint": {"host": host, "port": port},
        "ackPolicy": ACK_POLICY,
        "knownFailureCategories": KNOWN_FAILURE_CATEGORIES,
        **extra,
    }


def validate_9014_ack(ack_packet: str | None) -> dict:
    valid = bool(ack_packet and "CN=9014" in ack_packet and "MN=A110000_0001" in ack_packet)
    return {
        "required": True,
        "valid": valid,
        "cn": "9014" if ack_packet and "CN=9014" in ack_packet else None,
        "failureReason": None if valid else "Missing or invalid 9014 ACK from platform.",
    }


def fetch_json(url: str) -> object:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def find_protocol_log(logs: list[dict]) -> dict | None:
    for log in logs:
        if log.get("qn") == "20260706103512345" and log.get("mn") == "A110000_0001":
            return log
    return None


def find_telemetry_latest(rows: list[dict]) -> dict | None:
    return next((item for item in rows if item.get("sensorCode") == "w01010"), None)


def run_with_testclient(
    simulate_invalid_ack: bool = False,
    simulate_protocol_failure: bool = False,
    simulate_ui_evidence_failure: bool = False,
) -> dict:
    os.environ["APP_DATABASE_URL"] = f"sqlite:///./acceptance_smoke_{uuid.uuid4().hex}.db"

    from fastapi.testclient import TestClient

    from app.db.base import Base
    from app.db.session import SessionLocal, engine
    from app.main import app
    from app.services.seed import seed_database

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    with TestClient(app) as client:
        upload = client.post(
            "/api/v1/protocol/upload",
            content=BROKEN_PACKET if simulate_protocol_failure else REALTIME_PACKET,
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )
        if upload.status_code >= 400:
            return failure_result(
                "protocol",
                "Platform rejected the HJ212 packet before a valid acceptance result.",
                httpStatus=upload.status_code,
                response=upload.json(),
            )
        protocol_logs = client.get("/api/v1/protocol/logs")
        telemetry_latest = client.get("/api/v1/telemetry/latest")

    upload_data = upload.json()
    protocol_log = protocol_logs.json()[0]
    ack_packet = None if simulate_invalid_ack else upload_data.get("ackPacket")
    ack_validation = validate_9014_ack(ack_packet)
    if not ack_validation["valid"]:
        return failure_result(
            "acknowledgement",
            "Packet was accepted but no legal CN=9014 ACK was available.",
            ackValidation=ack_validation,
        )

    telemetry_rows = [] if simulate_ui_evidence_failure else telemetry_latest.json()
    telemetry_match = next((item for item in telemetry_rows if item["sensorCode"] == "w01010"), None)
    if telemetry_match is None:
        return failure_result(
            "ui evidence",
            "Protocol ACK is valid but latest telemetry evidence is missing.",
            protocolLog={
                "mn": protocol_log["mn"],
                "cn": protocol_log["cn"],
                "status": protocol_log["status"],
            },
            ackValidation=ack_validation,
        )
    engine.dispose()

    return {
        "status": "passed",
        "endpoint": {"host": FINAL_HOST, "port": FINAL_PORT},
        "ackPolicy": ACK_POLICY,
        "ackValidation": ack_validation,
        "knownFailureCategories": KNOWN_FAILURE_CATEGORIES,
        "uploaded": {
            "status": upload_data["status"],
            "cn": upload_data["cn"],
            "metricCount": upload_data["metricCount"],
        },
        "protocolLog": {
            "mn": protocol_log["mn"],
            "cn": protocol_log["cn"],
            "status": protocol_log["status"],
            "metricCount": protocol_log["metricCount"],
        },
        "telemetryLatest": {
            "sensorCode": telemetry_match["sensorCode"],
            "value": telemetry_match["value"],
            "recordedAt": telemetry_match["recordedAt"],
        },
    }


def run_with_tcp(host: str, port: int, api_base: str) -> dict:
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            sock.settimeout(5)
            sock.sendall(REALTIME_PACKET.encode("ascii"))
            ack_packet = sock.recv(4096).decode("ascii", errors="replace")
    except OSError as exc:
        return failure_result(
            "connection",
            f"Could not connect to TCP acceptance service: {exc}",
            host=host,
            port=port,
        )

    if ack_packet.startswith("ERROR:"):
        return failure_result(
            "protocol",
            "Platform rejected the TCP HJ212 packet before returning ACK.",
            host=host,
            port=port,
            tcpAckRaw=ack_packet,
        )

    ack_validation = validate_9014_ack(ack_packet)
    if not ack_validation["valid"]:
        return failure_result(
            "acknowledgement",
            "TCP packet was sent but no legal CN=9014 ACK was received.",
            host=host,
            port=port,
            tcpAckRaw=ack_packet,
            ackValidation=ack_validation,
        )

    try:
        protocol_logs = fetch_json(f"{api_base.rstrip('/')}/protocol/logs")
        telemetry_latest = fetch_json(f"{api_base.rstrip('/')}/telemetry/latest")
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return failure_result(
            "ui evidence",
            f"TCP ACK is valid but HTTP evidence could not be read: {exc}",
            host=host,
            port=port,
            tcpAckRaw=ack_packet,
            ackValidation=ack_validation,
        )

    protocol_log = find_protocol_log(protocol_logs if isinstance(protocol_logs, list) else [])
    telemetry_match = find_telemetry_latest(telemetry_latest if isinstance(telemetry_latest, list) else [])
    if protocol_log is None or telemetry_match is None:
        return failure_result(
            "ui evidence",
            "TCP ACK is valid but protocol log or latest telemetry evidence is missing.",
            host=host,
            port=port,
            tcpAckRaw=ack_packet,
            ackValidation=ack_validation,
            protocolLogFound=protocol_log is not None,
            telemetryFound=telemetry_match is not None,
        )

    return {
        "status": "passed",
        "endpoint": {"host": host, "port": port},
        "ackPolicy": ACK_POLICY,
        "ackValidation": ack_validation,
        "knownFailureCategories": KNOWN_FAILURE_CATEGORIES,
        "tcpAckRaw": ack_packet,
        "protocolLog": {
            "mn": protocol_log["mn"],
            "cn": protocol_log["cn"],
            "status": protocol_log["status"],
            "metricCount": protocol_log["metricCount"],
        },
        "telemetryLatest": {
            "sensorCode": telemetry_match["sensorCode"],
            "value": telemetry_match["value"],
            "recordedAt": telemetry_match["recordedAt"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the shortest platform acceptance smoke flow.")
    parser.add_argument("--mode", choices=["testclient", "tcp"], default="testclient")
    parser.add_argument("--host", default=FINAL_HOST)
    parser.add_argument("--port", type=int, default=FINAL_PORT)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument(
        "--simulate-invalid-ack",
        action="store_true",
        help="Exercise the final acceptance failure path for missing or invalid 9014 ACK.",
    )
    parser.add_argument(
        "--simulate-protocol-failure",
        action="store_true",
        help="Exercise the final acceptance failure path for rejected HJ212 packets.",
    )
    parser.add_argument(
        "--simulate-ui-evidence-failure",
        action="store_true",
        help="Exercise the final acceptance failure path for missing UI/API evidence.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    os.chdir(root / "backend")

    if args.mode == "testclient":
        result = run_with_testclient(
            simulate_invalid_ack=args.simulate_invalid_ack,
            simulate_protocol_failure=args.simulate_protocol_failure,
            simulate_ui_evidence_failure=args.simulate_ui_evidence_failure,
        )
    elif args.mode == "tcp":
        result = run_with_tcp(args.host, args.port, args.api_base)
    else:
        raise ValueError(f"Unsupported mode: {args.mode}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
