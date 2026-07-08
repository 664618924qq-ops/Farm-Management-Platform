# QA PC 验收证据

生成时间：2026-07-07 00:08

## GUI 首页证据

- 截图：`docs/qa_pc_homepage_screenshot.png`
- 截图可见：平台 TCP `127.0.0.1:9100`
- 截图可见：ACK 等待 `3 秒`
- 截图可见：实时入库开启，保存间隔 `30 秒`
- 截图可见：连接状态已连接，最后发送已收到 ACK

说明：首次 GUI 启动被本机 MySQL 密码配置阻塞，日志在 `docs/qa_pc_gui_stderr.log`；随后仅以临时进程环境变量和本机运行配置恢复方式完成取证，不涉及代码修改。

## 重复包证据

- 文本证据：`docs/qa_pc_service_evidence.txt`
- 结论：同一轮重复 payload 处理 `2` 条，只实际发送 `1` 次，第二条标记 `skipped`
- 失败重试：首条失败保持 `pending`，同批重复项暂缓保持 `pending`，不丢数据

## 上传 ACK 证据

- 文本证据：`docs/qa_pc_service_evidence.txt`
- 结论：真实 TCP `127.0.0.1:9100` 发送成功，收到合法 `CN=9014` ACK
- 最后一帧：文本证据中包含 `CN=2011`、`MN=A110000_0001`、`DataTime=20260706103000` 与因子编码
