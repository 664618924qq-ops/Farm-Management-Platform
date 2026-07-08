# Farm Management Platform

养殖场监测平台，用于 PC 采集端、平台接收端与 Web 管理端的联调、测试和验收。

## 正式验收口径

- Web 后端: `http://127.0.0.1:8000`
- TCP 接收端: `127.0.0.1:9100`
- Web 前端: `http://127.0.0.1:5173`
- ACK 判据: 平台成功接收、解析、入库后返回合法 HJ212 `CN=9014` ACK
- 历史端口 `127.0.0.1:8998` 仅为旧 PC 工程默认端口，不作为本轮正式验收口径。

## 启动方式

推荐使用 VS Code 任务:

```powershell
Ctrl + Shift + P
Tasks: Run Task
platform: start all
```

也可以分别启动:

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

## 环境检查

确认端口:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
Get-NetTCPConnection -LocalPort 9100 -State Listen
Get-NetTCPConnection -LocalPort 5173 -State Listen
```

确认当前仓库进程:

```text
C:\Users\DELL\Documents\Codex project\backend\.venv\Scripts\python.exe -m uvicorn app.main:app
C:\Users\DELL\Documents\Codex project\backend\.venv\Scripts\python.exe -m app.tcp.server
```

如果 `9100` 被旧进程占用，先停止旧进程，再用当前仓库的 `backend\.venv\Scripts\python.exe -m app.tcp.server` 启动。

## 验收守门

在平台服务已启动时运行:

```powershell
cd "C:\Users\DELL\Documents\Codex project"
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-acceptance.ps1 -SkipStartup
```

通过判据:

```text
[OK] TCP acceptance passed. CN=9014 ACK and platform evidence were verified.
```

## 验收证据顺序

1. PC 向 `127.0.0.1:9100` 发送固定报文。
2. PC 必须收到并校验合法 `CN=9014` ACK。
3. 总览页显示最近设备、接收状态、中文 ACK 状态和 ACK 包摘要。
4. 协议接收日志显示原始报文、`status=accepted`、`ackPacket` 包含 `CN=9014`。
5. 实时监测、数据查询和数据分析展示对应因子的最新数据。

## 当前产品重点

- 数据查询支持 `CN=2011` 实时数据和 `CN=2061` 小时数据。
- 因子筛选面向用户显示因子名称，例如水温、pH、溶解氧；编码仅作为内部兼容字段。
- 数据时间按北京时间展示，PC 端实时保存间隔支持 30 秒和 60 秒规整。
- 告警、巡检、协议日志和分析页面优先保证真实数据、时间正确性和中文可读性。
