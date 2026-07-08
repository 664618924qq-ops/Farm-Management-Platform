# 养虾监测后端服务

这是首版边缘采集服务骨架，包含以下能力预留：

- FastAPI 服务入口
- MySQL 数据模型
- 设备接入统一适配器接口
- 平台上传统一客户端接口
- 站点、设备、监测数据、告警、上传任务基础结构

## 1. 环境准备

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

复制配置模板：

```bash
copy .env.example .env
```

## 2. 初始化数据库

将 `database\shrimp_monitor.sql` 导入本地 MySQL：

```bash
mysql -u root -p < ..\database\shrimp_monitor.sql
```

## 3. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 4. 首版接口

- `GET /health` 健康检查
- `GET /api/v1/sites` 站点列表
- `GET /api/v1/devices` 设备列表
- `POST /api/v1/devices/{device_id}/collect` 触发一次模拟采集
- `GET /api/v1/telemetry/latest` 最新监测数据
- `POST /api/v1/platform/upload` 触发一次待上传数据上送

## 5. 下一步开发建议

- 将 `MockDeviceAdapter` 替换为真实 `Modbus RTU` / `Modbus TCP` 驱动
- 接入前端页面，做本地监控界面
- 按平台接口协议补齐上传签名和回执逻辑
- 增加调度器，周期性采集和自动上传
