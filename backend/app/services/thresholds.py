from __future__ import annotations

PRIMARY_STANDARD_CODE = "PROJECT_SURFACE_WATER_REQUIREMENTS"
PRIMARY_STANDARD_NAME = "本项目地表水技术要求目录"
GB11607_AUXILIARY_NOTE = "GB 11607-1989 仅作为特定渔业/养殖场景辅助参考。"

WATER_QUALITY_THRESHOLDS = {
    "w01010": {
        "name": "水温",
        "min": None,
        "max": None,
        "unit": "C",
        "basis": "依据本项目地表水技术要求目录及系统可配置阈值；水温默认用于趋势变化和站点自定义阈值判断。",
    },
    "w01014": {
        "name": "pH",
        "min": 6.0,
        "max": 9.0,
        "unit": "",
        "basis": "依据本项目地表水技术要求目录及系统可配置阈值；pH 默认参考地表水环境质量口径，现场可按站点调整。",
    },
    "w01001": {
        "name": "溶解氧",
        "min": 5.0,
        "max": None,
        "unit": "mg/L",
        "basis": f"依据本项目地表水技术要求目录及系统可配置阈值；{GB11607_AUXILIARY_NOTE}",
    },
    "w01017": {
        "name": "电导率",
        "min": None,
        "max": None,
        "unit": "mS/cm",
        "basis": "依据本项目地表水技术要求目录及系统可配置阈值；电导率默认用于趋势观察，可按站点背景值配置阈值。",
    },
    "w01003": {
        "name": "浊度",
        "min": None,
        "max": None,
        "unit": "NTU",
        "basis": "依据本项目地表水技术要求目录及系统可配置阈值；浊度默认用于趋势观察，可按站点背景值配置阈值。",
    },
    "w01019": {
        "name": "盐度",
        "min": None,
        "max": None,
        "unit": "g/L",
        "basis": f"依据本项目地表水技术要求目录及系统可配置阈值；盐度适宜范围与养殖品种相关，{GB11607_AUXILIARY_NOTE}",
    },
    "w01018": {
        "name": "高锰酸盐指数",
        "min": None,
        "max": 6.0,
        "unit": "mg/L",
        "basis": "依据本项目地表水技术要求目录及系统可配置阈值；此处默认参考地表水 III 类水限值，系统可配置。",
    },
    "w21003": {
        "name": "氨氮",
        "min": None,
        "max": 1.0,
        "unit": "mg/L",
        "basis": "依据本项目地表水技术要求目录及系统可配置阈值；此处默认参考地表水 III 类水限值，系统可配置。",
    },
    "w21011": {
        "name": "总磷",
        "min": None,
        "max": 0.2,
        "unit": "mg/L",
        "basis": "依据本项目地表水技术要求目录及系统可配置阈值；此处默认参考地表水 III 类水限值，湖库等场景需单独配置。",
    },
    "w21001": {
        "name": "总氮",
        "min": None,
        "max": 1.0,
        "unit": "mg/L",
        "basis": "依据本项目地表水技术要求目录及系统可配置阈值；此处默认参考地表水 III 类水限值，系统可配置。",
    },
}


def evaluate_threshold(sensor_code: str, value: float | None, history: list[float] | None = None) -> dict:
    if value is None:
        return {
            "level": "missing",
            "qualityLabel": "缺失/异常",
            "ruleType": "missing",
            "message": "当前值缺失或无法解析。",
            "basis": "平台数据完整性规则；标准版本字段保留用于后续规则升级。",
            "standardCode": PRIMARY_STANDARD_CODE,
            "threshold": None,
        }

    config = WATER_QUALITY_THRESHOLDS.get(sensor_code)
    history_values = history or []
    if len(history_values) >= 5 and max(history_values[-5:]) == min(history_values[-5:]):
        return {
            "level": "constant",
            "qualityLabel": "疑似恒值",
            "ruleType": "constant",
            "message": "最近 5 条数据完全一致，建议检查传感器是否卡值或采集链路是否重复上报。",
            "basis": "平台可配置数据质量规则，窗口大小默认 5，可后续配置；标准版本字段保留用于后续规则升级。",
            "standardCode": PRIMARY_STANDARD_CODE,
            "threshold": {"windowSize": 5, "standard": PRIMARY_STANDARD_NAME, "standardCode": PRIMARY_STANDARD_CODE},
        }

    if len(history_values) >= 6:
        baseline = history_values[:-1]
        avg = sum(baseline) / len(baseline)
        variance = sum((item - avg) ** 2 for item in baseline) / len(baseline)
        std = variance**0.5
        if std > 0 and abs(value - avg) > 3 * std:
            return {
                "level": "outlier",
                "qualityLabel": "疑似离群",
                "ruleType": "outlier",
                "message": "当前值偏离近期均值超过 3 倍标准差，建议复核传感器和现场状态。",
                "basis": "平台可配置数据质量规则，默认采用 3σ 离群判断；标准版本字段保留用于后续规则升级。",
                "standardCode": PRIMARY_STANDARD_CODE,
                "threshold": {
                    "sigma": 3,
                    "baselineAvg": round(avg, 3),
                    "baselineStd": round(std, 3),
                    "standard": PRIMARY_STANDARD_NAME,
                    "standardCode": PRIMARY_STANDARD_CODE,
                },
            }

    if config is None:
        return {
            "level": "normal",
            "qualityLabel": "正常",
            "ruleType": "none",
            "message": "暂无该指标阈值配置，仅展示趋势。",
            "basis": "未配置。",
            "standardCode": PRIMARY_STANDARD_CODE,
            "threshold": None,
        }

    lower = config.get("min")
    upper = config.get("max")
    threshold = {
        "min": lower,
        "max": upper,
        "unit": config["unit"],
        "standard": PRIMARY_STANDARD_NAME,
        "standardCode": PRIMARY_STANDARD_CODE,
    }
    if lower is not None and value < float(lower):
        return {
            "level": "exceeded",
            "qualityLabel": "超标",
            "ruleType": "threshold",
            "message": f"{config['name']}低于当前配置下限 {lower}{config['unit']}，建议按本项目地表水技术要求目录和现场场景复核。",
            "basis": config["basis"],
            "standardCode": PRIMARY_STANDARD_CODE,
            "threshold": threshold,
        }
    if upper is not None and value > float(upper):
        return {
            "level": "exceeded",
            "qualityLabel": "超标",
            "ruleType": "threshold",
            "message": f"{config['name']}高于当前配置上限 {upper}{config['unit']}，建议按本项目地表水技术要求目录和现场场景复核。",
            "basis": config["basis"],
            "standardCode": PRIMARY_STANDARD_CODE,
            "threshold": threshold,
        }
    return {
        "level": "normal",
        "qualityLabel": "正常",
        "ruleType": "threshold",
        "message": f"{config['name']}处于当前系统配置范围内。",
        "basis": config["basis"],
        "standardCode": PRIMARY_STANDARD_CODE,
        "threshold": threshold,
    }
