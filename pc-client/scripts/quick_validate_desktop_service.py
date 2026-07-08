from __future__ import annotations

from desktop_app.services import data_service as service_module
from desktop_app.services.data_service import DesktopDataService
from tests.test_desktop_data_service import build_test_session_factory


def run_check(name: str, func) -> tuple[bool, str]:
    try:
        func()
        return True, f"[PASS] {name}"
    except Exception as exc:  # pragma: no cover
        return False, f"[FAIL] {name}: {exc}"


def main() -> int:
    session_factory = build_test_session_factory()
    service_module.SessionLocal = session_factory
    service = DesktopDataService()

    results: list[tuple[bool, str]] = []

    def check_serial_binding_delete_guard() -> None:
        service.save_acquisition_profile(
            "RTU模板-删除校验",
            "modbus_rtu",
            "serial",
            "默认串口1",
            5,
            "float32",
            "30031",
            False,
        )
        try:
            service.delete_serial_profile("默认串口1")
        except ValueError as exc:
            if "Modbus RTU" not in str(exc):
                raise
        else:
            raise AssertionError("expected bound serial profile deletion to be rejected")

    def check_factor_register_guard() -> None:
        try:
            service.save_factor_bindings(
                1,
                [
                    {
                        "id": "",
                        "metric_code": "water_temp",
                        "metric_name": "水温",
                        "metric_unit": "C",
                        "register_address": "40A01",
                        "lower_limit": "",
                        "upper_limit": "",
                    }
                ],
            )
        except ValueError as exc:
            if "寄存器地址" not in str(exc):
                raise
        else:
            raise AssertionError("expected non-numeric register address to be rejected")

    def check_acquisition_profile_register_guard() -> None:
        try:
            service.save_acquisition_profile(
                "RTU模板-寄存器校验",
                "modbus_rtu",
                "serial",
                "默认串口1",
                5,
                "float32",
                "30A01",
                False,
            )
        except ValueError as exc:
            if "寄存器地址" not in str(exc):
                raise
        else:
            raise AssertionError("expected non-numeric acquisition register to be rejected")

    results.append(run_check("RTU串口删除依赖校验", check_serial_binding_delete_guard))
    results.append(run_check("因子寄存器数字校验", check_factor_register_guard))
    results.append(run_check("设备模板寄存器数字校验", check_acquisition_profile_register_guard))

    for _, message in results:
        print(message)

    return 0 if all(success for success, _ in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
