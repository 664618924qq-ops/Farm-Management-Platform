# 最终验收单模板

## 1. 基本信息

- 项目名称：
- 验收日期：
- 验收地点：
- 验收人员：
- 平台版本/提交：
- PC 端版本/提交：

## 2. 环境检查

执行命令：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-env.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-ports.ps1
```

检查结果：

- MySQL `127.0.0.1:3306`：通过 / 不通过
- 后端 `127.0.0.1:8000`：通过 / 不通过
- TCP 接收 `127.0.0.1:9100`：通过 / 不通过
- Web `127.0.0.1:5173`：通过 / 不通过

必填证据：

- 环境检查输出：
- 端口检查输出：

## 3. 平台守门验收

执行命令：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-acceptance.ps1
```

如果服务已由部署同事启动：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-acceptance.ps1 -SkipStartup
```

通过条件：

- 控制台出现 `[OK] TCP acceptance passed. CN=9014 ACK and platform evidence were verified.`
- JSON 中 `status = passed`
- JSON 中 `ackValidation.valid = true`
- JSON 中 `ackValidation.cn = 9014`
- JSON 中 `protocolLog.status = accepted`
- JSON 中 `telemetryLatest.sensorCode = w01010`

必填证据：

- `check-acceptance.ps1` 控制台输出：
- JSON 文件路径：`logs\acceptance\tcp-acceptance-________.json`
- JSON 摘要：

## 4. PC 发送验收

正式口径：

- 目标地址：`127.0.0.1`
- 目标端口：`9100`
- ACK 策略：必须收到合法 `CN=9014`
- ACK 等待建议：`3.0s`

PC 发送结果：

- 发送时间：
- 当前连接状态：
- 最后一次发送结果：
- ACK 状态：
- 最后一帧报文摘要：

必填证据：

- PC 首页连接/发送状态截图：
- PC ACK 摘要：
- PC 最后一帧报文：

## 5. ACK 校验

通过条件：

- PC 端收到平台 ACK
- ACK 原文包含 `CN=9014`
- ACK 中 `MN=A110000_0001`
- PC 端未将缺失 ACK 判为成功

必填证据：

- ACK 原文或摘要：
- PC ACK 校验状态截图：

## 6. 平台页面证据

协议日志页应看到：

- `MN = A110000_0001`
- `CN = 2011`
- `status = accepted`
- `ackPacket` 包含 `CN=9014`
- `metricCount = 5`

实时监测页应看到：

- `sensorCode = w01010`
- 最新值已更新
- 记录时间可对应本次报文

必填证据：

- 协议日志页截图：
- 实时监测页截图：

## 7. 失败重跑规则

只允许以下情况立即重跑一次：

- 首次失败分类为 `ui evidence`
- JSON 中 `ackValidation.valid = true`
- JSON 中 `ackValidation.cn = 9014`
- JSON 中 `tcpAckRaw` 包含 `CN=9014`

重跑要求：

- 保留第一次 JSON 文件
- 保留第二次 JSON 文件
- 第二次仍失败时，按真实失败处理

重跑记录：

- 第一次 JSON 路径：
- 第二次 JSON 路径：
- 最终处理结论：

## 8. 红线条件

出现以下任一情况，不建议验收通过：

- `127.0.0.1:9100` 不可连接
- 未收到合法 `CN=9014` ACK
- 固定 `CN=2011` 报文被平台拒收或解析失败
- `ui evidence` 连续两次失败
- 缺少 `logs\acceptance\tcp-acceptance-*.json` 证据
- 验收过程使用 `8998` 或其他非正式端口

## 9. 最终结论

验收结论：

- 通过 / 不通过 / 有条件通过

签字结论模板：

- 通过：本次验收守门命令通过，PC ACK、平台协议日志、实时监测页面证据完整，同意验收通过。
- 不通过：本次验收存在红线问题，失败分类为 ________，关键证据缺失或不满足最终验收口径，不建议验收通过。

问题记录：

- 问题 1：
- 问题 2：
- 问题 3：

整改要求：

- 整改项 1：
- 整改项 2：

签字确认：

- 产品负责人：
- 平台负责人：
- PC 端负责人：
- 测试负责人：
- 日期：
