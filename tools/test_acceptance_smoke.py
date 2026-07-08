import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_acceptance_smoke_script_passes_and_reports_protocol_and_telemetry() -> None:
    result = subprocess.run(
        [
            str(ROOT / "backend" / ".venv" / "Scripts" / "python.exe"),
            str(ROOT / "tools" / "acceptance_smoke.py"),
            "--mode",
            "testclient",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "passed"
    assert payload["endpoint"]["host"] == "127.0.0.1"
    assert payload["endpoint"]["port"] == 9100
    assert payload["ackPolicy"] == "required"
    assert payload["ackValidation"]["required"] is True
    assert payload["ackValidation"]["valid"] is True
    assert payload["ackValidation"]["cn"] == "9014"
    assert payload["uploaded"]["cn"] == "2011"
    assert payload["protocolLog"]["status"] == "accepted"
    assert payload["protocolLog"]["mn"] == "A110000_0001"
    assert payload["telemetryLatest"]["sensorCode"] == "w01010"


def test_acceptance_smoke_script_rejects_missing_or_invalid_ack() -> None:
    result = subprocess.run(
        [
            str(ROOT / "backend" / ".venv" / "Scripts" / "python.exe"),
            str(ROOT / "tools" / "acceptance_smoke.py"),
            "--mode",
            "testclient",
            "--simulate-invalid-ack",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert payload["failureCategory"] == "acknowledgement"
    assert payload["ackValidation"]["required"] is True
    assert payload["ackValidation"]["valid"] is False


def test_acceptance_smoke_script_classifies_protocol_failure() -> None:
    result = subprocess.run(
        [
            str(ROOT / "backend" / ".venv" / "Scripts" / "python.exe"),
            str(ROOT / "tools" / "acceptance_smoke.py"),
            "--mode",
            "testclient",
            "--simulate-protocol-failure",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert payload["failureCategory"] == "protocol"


def test_acceptance_smoke_script_classifies_ui_evidence_failure() -> None:
    result = subprocess.run(
        [
            str(ROOT / "backend" / ".venv" / "Scripts" / "python.exe"),
            str(ROOT / "tools" / "acceptance_smoke.py"),
            "--mode",
            "testclient",
            "--simulate-ui-evidence-failure",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert payload["failureCategory"] == "ui evidence"


def test_acceptance_smoke_tcp_mode_classifies_connection_failure() -> None:
    result = subprocess.run(
        [
            str(ROOT / "backend" / ".venv" / "Scripts" / "python.exe"),
            str(ROOT / "tools" / "acceptance_smoke.py"),
            "--mode",
            "tcp",
            "--host",
            "127.0.0.1",
            "--port",
            "1",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert payload["failureCategory"] == "connection"
    assert payload["endpoint"]["port"] == 1
