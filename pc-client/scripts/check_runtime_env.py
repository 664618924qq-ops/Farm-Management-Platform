from __future__ import annotations

import importlib
import sys
from pathlib import Path


REQUIRED_MODULES = [
    ("dotenv", "python-dotenv"),
    ("sqlalchemy", "sqlalchemy"),
    ("pymysql", "pymysql"),
    ("serial", "pyserial"),
    ("pymodbus", "pymodbus"),
    ("PySide6", "PySide6"),
]


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    missing: list[str] = []

    print("养虾监测工具启动前检查")
    print(f"Python: {sys.executable}")
    print(f"项目目录: {project_root}")

    for module_name, package_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
            print(f"[OK] {package_name}")
        except Exception:
            missing.append(package_name)
            print(f"[缺失] {package_name}")

    if missing:
        print()
        print("当前环境缺少以下依赖：")
        for package_name in missing:
            print(f" - {package_name}")
        print()
        print("请先执行：")
        print(r".venv\Scripts\python.exe -m pip install -r requirements.txt")
        return 1

    print()
    print("运行环境检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
