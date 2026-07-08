# 养殖场监测平台

本项目用于最终联调验收，正式口径只认这一套：

- Web 后端：`http://127.0.0.1:8000`
- TCP 接收端：`127.0.0.1:9100`
- Web 前端：`http://127.0.0.1:5173`
- ACK 判据：平台成功接收、解析、入库后必须返回合法 HJ212 `CN=9014` ACK

`127.0.0.1:8998` 仅是旧 PC 工程历史默认端口，不作为本轮正式验收口径。

## 启动方式

推荐使用 VS Code 一键任务：

```powershell
Ctrl + Shift + P
Tasks: Run Task
platform: start all
```

也可以分别启动：

```powershell
cd "C:\Users\DELL\Documents\Codex project\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8000 --reload --reload-dir app
```

```powershell
cd "C:\Users\DELL\Documents\Codex project\backend"
.\.venv\Scripts\python.exe -m app.tcp.server
```

```powershell
cd "C:\Users\DELL\Documents\Codex project\frontend"
npm run dev
```

## 确认命中当前仓库代码

Web 后端进程应包含：

```text
C:\Users\DELL\Documents\Codex project\backend\.venv\Scripts\python.exe -m uvicorn app.main:app
```

TCP 接收进程应包含：

```text
C:\Users\DELL\Documents\Codex project\backend\.venv\Scripts\python.exe -m app.tcp.server
```

确认端口：

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
Get-NetTCPConnection -LocalPort 9100 -State Listen
Get-NetTCPConnection -LocalPort 5173 -State Listen
```

如果 `9100` 被旧进程占用，先停掉旧进程，再用当前仓库的 `backend\.venv\Scripts\python.exe -m app.tcp.server` 启动。

## 最终守门命令

在平台服务已启动时运行：

```powershell
cd "C:\Users\DELL\Documents\Codex project"
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-acceptance.ps1 -SkipStartup
```

通过判据：输出 `[OK] TCP acceptance passed. CN=9014 ACK and platform evidence were verified.`

## 页面与 API 口径

总览页面向验收人员展示中文 ACK 证据：

- ACK 状态：`ACK 正常（已收到 CN=9014）`
- ACK 包摘要：`平台已返回 CN=9014 ACK`

后端 API 为了兼容 QA/部署守门脚本，保留机器值：

- `lastAckStatus = valid_9014_ack`
- `lastAckSummary = CN=9014 ACK returned`

PC 侧 ACK 等待建议为 `3s`，最低不建议低于 `1s`；`0.2s` 容易把平台正常写库和回包抖动误判为 ACK 缺失。

## 验收证据顺序

1. PC 向 `127.0.0.1:9100` 发送固定报文
2. PC 必须收到并校验合法 `CN=9014` ACK
3. 总览页“联调状态看板”显示最近设备、接收状态、中文 ACK 状态、中文 ACK 包摘要
4. 协议接收日志显示原始报文、`status=accepted`、`ackPacket` 包含 `CN=9014`
5. 实时监测显示对应 `w010*` 指标最新值

截图与证据采集清单见 [docs/最终验收截图证据清单.md](./docs/最终验收截图证据清单.md)。

详细口径见 [docs/平台联调验收口径.md](./docs/平台联调验收口径.md)。
