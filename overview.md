# Moling 飞书告警系统 — 完成报告

## 做了什么

补齐了完整的 **Prometheus → AlertManager → feishu-bridge → 飞书卡片** 告警链路。每条飞书消息都是自包含的故障诊断报告，不需要打开 Grafana 就能处理问题。

## 新增文件

| 文件 | 作用 |
|------|------|
| `docker/alert_rules.yml` | 15 条告警规则，覆盖可用性/错误率/延迟/资源/数据库/AI/安全/任务队列 |
| `docker/alertmanager.yml` | 告警路由：critical 即时发、warning 聚合发，含抑制规则防刷屏 |
| `docker/feishu-alert-bridge.py` | Python Flask 服务，AlertManager webhook → 飞书交互卡片 |
| `docker/feishu.tmpl` | AlertManager 通知模板（fallback） |
| `docker/Dockerfile.feishu-bridge` | feishu-bridge 容器镜像 |
| `docker/.env.example` | 飞书 Webhook URL 配置模板 |

## 修改文件

| 文件 | 变更 |
|------|------|
| `docker/prometheus.yml` | 启用 alertmanager:9093 + 加载 alert_rules.yml |
| `docker/docker-compose.yml` | 新增 alertmanager + feishu-bridge 服务 + alertmanagerdata 卷 |

## 飞书消息包含什么

每条告警卡片自带：

- **标题**: 带图标和严重级别（🔴/🟡/🟢）
- **当前状态**: 具体指标数值
- **影响范围**: 对用户/业务的影响
- **处理步骤**: 可直接复制执行的 runbook 命令
- **Grafana 链接**: [点击查看大盘]（需要时一键跳转）
- **GitHub Actions 按钮**: 快速跳转到 CI/CD

## 怎么启用

```bash
# 1. 配置飞书 Webhook
cp docker/.env.example docker/.env
# 编辑 docker/.env，填入实际的 FEISHU_WEBHOOK_URL

# 2. 重新部署
docker compose -f docker/docker-compose.yml up -d

# 3. 验证
curl http://localhost:9094/health
```

## 告警规则覆盖

| 类别 | 告警数 | 示例 |
|------|--------|------|
| 服务可用性 | 2 | BackendDown, FrontendDown |
| API 错误 | 2 | High5xxRate, High4xxRate |
| 响应延迟 | 2 | HighP95Latency, HighP99Latency |
| 系统资源 | 3 | HighCPU, HighMemory, DiskFull |
| 数据库 | 2 | ConnectionPoolExhausted, SlowQueries |
| AI 服务 | 2 | AIGenerationFailed, AIGenerationSlow |
| 安全 | 1 | SSLCertificateExpiring |
| 异步任务 | 1 | TaskQueueBacklog |
