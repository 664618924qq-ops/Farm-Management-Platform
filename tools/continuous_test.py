from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


PLATFORM_THREAD_ID = "019f26d1-0276-7f33-b77a-29641bec570e"
PC_THREAD_ID = "019f3501-6159-7d91-a494-899dec8911a9"
REPORT_DIR = Path("reports") / "continuous-tests"


@dataclass
class TestResult:
    __test__ = False

    name: str
    command: str
    cwd: str
    exit_code: int
    duration_seconds: float
    output: str

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


def classify_failure_targets(result: TestResult) -> list[str]:
    text = f"{result.name}\n{result.command}\n{result.cwd}\n{result.output}".lower()
    targets = [PLATFORM_THREAD_ID]
    pc_keywords = (
        "tcp",
        "hj212",
        "protocol",
        "cn=2011",
        "cn=2061",
        "9014",
        "ack",
        "socket",
        "upload",
    )
    if any(keyword in text for keyword in pc_keywords):
        targets.append(PC_THREAD_ID)
    return targets


def build_failure_report(results: list[TestResult]) -> str:
    failed = [result for result in results if not result.passed]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# 持续测试发现问题",
        "",
        f"- 发现时间：{now}",
        f"- 失败套件数：{len(failed)}",
        "",
    ]
    for result in failed:
        tail = "\n".join(result.output.splitlines()[-60:])
        lines.extend(
            [
                f"## {result.name}",
                "",
                f"- 退出码：{result.exit_code}",
                f"- 耗时：{result.duration_seconds:.1f}s",
                "- 复现命令：",
                "",
                "```powershell",
                f"cd {result.cwd}",
                result.command,
                "```",
                "",
                "- 日志摘要：",
                "",
                "```text",
                tail.strip() or "(没有输出)",
                "```",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def run_suite(name: str, command: str, cwd: Path, timeout_seconds: int) -> TestResult:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
        )
        exit_code = completed.returncode
        output = completed.stdout
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        output = (exc.stdout or "") + f"\nTIMEOUT after {timeout_seconds}s"
    duration = time.monotonic() - started
    return TestResult(
        name=name,
        command=command,
        cwd=str(cwd),
        exit_code=exit_code,
        duration_seconds=duration,
        output=output,
    )


def default_suites(root: Path) -> list[tuple[str, str, Path, int]]:
    backend_python = root / "backend" / ".venv" / "Scripts" / "python.exe"
    backend_pytest = f'"{backend_python}" -m pytest'
    return [
        ("backend", backend_pytest, root / "backend", 180),
        ("frontend-test", "npm run test", root / "frontend", 180),
        ("frontend-build", "npm run build", root / "frontend", 240),
    ]


def write_reports(results: list[TestResult], root: Path) -> tuple[Path, Path | None]:
    report_dir = root / REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    latest_json = report_dir / "latest.json"
    latest_md = report_dir / "latest.md"
    latest_targets = report_dir / "latest-targets.json"
    latest_json.write_text(
        json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    failed = [result for result in results if not result.passed]
    if failed:
        targets = sorted({target for result in failed for target in classify_failure_targets(result)})
        latest_targets.write_text(json.dumps(targets, ensure_ascii=False, indent=2), encoding="utf-8")
        latest_md.write_text(build_failure_report(results), encoding="utf-8")
        return latest_json, latest_md
    latest_targets.write_text("[]\n", encoding="utf-8")
    latest_md.write_text("# 持续测试通过\n\n本轮后端、前端测试和前端构建均通过。\n", encoding="utf-8")
    return latest_json, None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run continuous tests for the livestock platform.")
    parser.add_argument("--root", default=".", help="Project root directory.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    results = [run_suite(*suite) for suite in default_suites(root)]
    _, failure_report = write_reports(results, root)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name} ({result.duration_seconds:.1f}s)")
    if failure_report:
        print(f"Failure report: {failure_report}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
