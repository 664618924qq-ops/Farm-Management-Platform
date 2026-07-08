# PC 客户端交付包说明

## 交付目录建议

平台交付包中建议放置为：

```text
pc-client/
  app/
  desktop_app/
  docs/
  scripts/
  requirements.txt
  start.ps1
  .env.example
  README.md
```

必须包含：

- `app/`：协议组包、上传客户端、采集和数据库模型等核心代码。
- `desktop_app/`：PC 桌面软件入口和界面代码。
- `scripts/check_runtime_env.py`：启动前依赖检查。
- `requirements.txt`：Python 依赖清单。
- `start.ps1`：验收推荐启动入口。
- `.env.example`：首次启动生成 `.env` 的模板。

建议包含：

- `docs/pc_acceptance_steps.md`：现场验收步骤。
- `docs/pc_delivery_package.md`：本说明文件。
- `README.md`：项目基础说明。

可不带：

- `.venv/`：本机虚拟环境，交付包内不建议携带。
- `.pytest_cache/`、`__pycache__/`：运行缓存。
- `tests/`：验收运行不需要；若交付方要求可单独附带。
- `ack_probe_result.json`、`tmp_ack_probe.json`、`pytest_verify.log`、`uvicorn.*.log`：本地调试产物。

## 启动入口

在 `pc-client/` 目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

`start.ps1` 会执行以下动作：

1. 如果 `.env` 不存在，则从 `.env.example` 复制生成。
2. 写入并确认正式验收口径：
   - `PLATFORM_HOST='127.0.0.1'`
   - `PLATFORM_PORT='9100'`
   - `PLATFORM_ACK_TIMEOUT_SECONDS='3.0'`
3. 如果 `.venv` 不存在，则创建本地虚拟环境。
4. 检查依赖，缺失时执行 `pip install -r requirements.txt`。
5. 启动 PC 桌面端：`python -m desktop_app.main`。

## 验收口径

PC 侧最终默认值为：

- TCP 目标：`127.0.0.1:9100`
- ACK 策略：必须收到合法 HJ212 `CN=9014`
- ACK 等待：`3.0` 秒
- 固定演示 MN：`A110000_0001`
- 实时保存间隔默认值：`30` 秒，可在 PC “参数设置 -> 基本参数”中通过下拉框选择 `30 秒` 或 `60 秒`。

## 数据分析与质量提示

PC 端提供“数据分析”页面，口径统一为“本项目地表水技术要求目录 + 可配置阈值”。GB 3838 可作为默认阈值参考背景，GB 11607 不作为 PC 本地主判断依据。第一版展示最近 24 小时重点指标趋势：

- 水温 `w01010`
- 溶解氧 `w01014`
- pH `w01001`
- 浊度 `w01003`
- 电导率 `w01019`
- 预留：高锰酸盐指数/CODMn `w01018`、氨氮 `w21003`、总磷 `w21011`、总氮 `w21001`

本地质量提示包括：超标、疑似离群、疑似恒值。阈值和规则可通过系统设置项扩展：

- `analysis_thresholds_json`：指标上下限、来源说明和建议文案。
- `analysis_quality_rules_json`：离群和恒值判断参数。

PC 侧文案保持“参考/建议/请复核现场”，只提供本地提示和上传质量标记预留，最终告警归档、短信通知和处置闭环以平台为准。

若发送失败，请收集：

- PC 首页连接状态、最后发送结果、ACK 状态。
- PC 首页“离线缓存/补传”状态。
- PC “数据分析”质量提示截图。
- “查看最后一帧”中的原始报文。
- `.env` 中的 `PLATFORM_HOST`、`PLATFORM_PORT`、`PLATFORM_ACK_TIMEOUT_SECONDS`。
- 平台 TCP 服务监听端口、原始收包日志和 ACK 写回日志。
