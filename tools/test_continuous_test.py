from tools.continuous_test import TestResult, build_failure_report, classify_failure_targets


PLATFORM_THREAD_ID = "019f26d1-0276-7f33-b77a-29641bec570e"
PC_THREAD_ID = "019f3501-6159-7d91-a494-899dec8911a9"


def test_classifies_protocol_failures_for_both_platform_and_pc_threads():
    result = TestResult(
        name="backend",
        command="pytest tests/test_protocol_upload.py tests/test_hj212.py",
        cwd="backend",
        exit_code=1,
        duration_seconds=1.2,
        output="FAILED tests/test_hj212.py::test_tcp_ack",
    )

    targets = classify_failure_targets(result)

    assert PLATFORM_THREAD_ID in targets
    assert PC_THREAD_ID in targets


def test_classifies_frontend_failures_for_platform_thread_only():
    result = TestResult(
        name="frontend-test",
        command="npm run test",
        cwd="frontend",
        exit_code=1,
        duration_seconds=0.8,
        output="DashboardView failed to render",
    )

    targets = classify_failure_targets(result)

    assert targets == [PLATFORM_THREAD_ID]


def test_failure_report_contains_reproduction_command_and_trimmed_log():
    result = TestResult(
        name="backend",
        command="pytest",
        cwd="backend",
        exit_code=1,
        duration_seconds=2.5,
        output="\n".join(f"line {index}" for index in range(80)),
    )

    report = build_failure_report([result])

    assert "持续测试发现问题" in report
    assert "cd backend" in report
    assert "pytest" in report
    assert "line 79" in report
    assert "line 0" not in report
