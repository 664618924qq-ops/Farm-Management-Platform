# 验收前必跑命令清单

## 最终 PASS 口径

验收当天只认 `check-acceptance.ps1` 的 PASS 输出和对应 JSON 证据。

正式守门命令：

```powershell
cd "C:\Users\DELL\Documents\Codex project"
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-acceptance.ps1
```

如果服务已经由部署同事启动，只验证现有服务：

```powershell
cd "C:\Users\DELL\Documents\Codex project"
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-acceptance.ps1 -SkipStartup
```

通过时必须同时满足：

- 控制台出现 `[OK] TCP acceptance passed. CN=9014 ACK and platform evidence were verified.`
- `logs\acceptance\tcp-acceptance-*.json` 中 `status = passed`
- `ackValidation.valid = true`
- `ackValidation.cn = 9014`
- `protocolLog.status = accepted`
- `telemetryLatest.sensorCode = w01010`

## 执行顺序

1. 环境检查：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-env.ps1
```

2. 端口检查：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-ports.ps1
```

3. 启动并验收：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-acceptance.ps1
```

## 页面与 API 口径

总览页面展示中文 ACK 证据：

- ACK 状态：`ACK 正常（已收到 CN=9014）`
- ACK 包摘要：`平台已返回 CN=9014 ACK`

后端 API 和 QA/部署守门脚本保留机器值：

- `lastAckStatus = valid_9014_ack`
- `lastAckSummary = CN=9014 ACK returned`

截图与证据采集清单见 [最终验收截图证据清单.md](./最终验收截图证据清单.md)。

## 失败处理规则

守门命令只使用 4 类失败：

- `connection`：无法连接 `127.0.0.1:9100` 或命中错误服务
- `protocol`：平台收到报文但协议解析失败
- `acknowledgement`：报文已发出或已接收，但没有合法 `CN=9014` ACK
- `ui evidence`：ACK 合法，但协议日志或实时监测证据缺失

如果第一次失败是 `ui evidence`，且 JSON 中同时满足：

- `ackValidation.valid = true`
- `ackValidation.cn = 9014`
- `tcpAckRaw` 包含 `CN=9014`

允许立即重跑一次 `check-acceptance.ps1`，并保留两次 `logs\acceptance\tcp-acceptance-*.json`。

如果第二次仍失败，则按真实失败处理，不再继续重跑。

## 红线条件

以下任一情况出现，不建议验收通过：

- `connection`：`127.0.0.1:9100` 不可连接，或端口不是平台 TCP 接收服务
- `acknowledgement`：未收到合法 `CN=9014` ACK
- `protocol`：固定 `CN=2011` 验收报文被平台拒收或解析失败
- `ui evidence` 连续两次失败：ACK 合法但协议日志或实时监测证据仍缺失
- JSON 证据缺失：没有生成 `logs\acceptance\tcp-acceptance-*.json`
- 端口口径漂移：验收过程使用 `8998` 或其他非正式端口

## PC ACK 等待建议

PC 侧默认 ACK 等待建议为 `3s`，最低不建议低于 `1s`。

原因：

- `0.2s` 容易把平台慢响应误判为 ACK 缺失
- `3s` 对本机验收仍然很快，且能覆盖服务首次响应、数据库写入和 API 证据读取的轻微抖动
- 超过 `3s` 仍未收到合法 `CN=9014`，统一归因为 `acknowledgement`
