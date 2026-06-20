# 墨灵 (Moling) 文档索引

> **最后更新**: 2026-06-21 | **文档目录**: `docs/`

---

## 📋 核心文档（5 份，平铺）

| 文档 | 版本 | 说明 | 适用 |
|:-----|:----:|:-----|:----:|
| `ARCHITECTURE.md` | 1.4.0 | 系统架构 — 部署拓扑、数据流、技术栈、安全、DAO/Worker/Celery 规范 | 全体 |
| `SPECIFICATIONS.md` | 2.1.0 | 功能规格 — P0/P1、卡牌算法、架构加固、质量门禁 | 后端 |
| `DEPLOYMENT.md` | 2.1.0 | 部署指南 — Docker/Nginx/云服务器/环境变量全量 | 运维 |
| `SECURITY_HARDENING.md` | 1.1.0 | 安全加固 — Rate Limit/JWT/HTTPS/Content-Length/RefreshToken | 安全 |
| `ONBOARDING.md` | 1.2.0 | 开发上手 — 环境搭建、env 配置、Windows 适配、常见问题 | 新人 |

---

## 🎨 design/ — 设计与前端文档（5 份）

| 文档 | 说明 |
|:-----|:-----|
| `design-decisions.md` | 前端视觉设计决策（ADR 格式，8 主题系统） |
| `前端重建方案.md` | 前端重建技术方案（v1.0，Next.js 15 架构） |
| `VIBE_WRITING_DESIGN.md` | Vibe Writing 产品设计（Agent of Agents、交互模型） |
| `DESIGN.md` | 设计系统（暗色主题、色阶、排版、组件样式） |
| `fe-specs.md` | 前端 Phase 4 & 健康监控生产级规格 |

---

## 🖥️ operations/ — 运维手册（5 份）

| 文档 | 版本 | 说明 |
|:-----|:----:|:-----|
| `RUNBOOK.md` | 1.1.0 | 故障处理 SOP（7 种故障 + 健康检查命令） |
| `BACKUP_STRATEGY.md` | — | 数据库备份与灾备策略 |
| `DISASTER_RECOVERY_LOG.md` | — | 灾备演练记录 |
| `MONITORING_SETUP.md` | 1.0 | Sentry 监控接入配置 |
| `CI_CD_SETUP.md` | — | GitHub Actions CI/CD Secrets 配置 |

---

## 📊 reports/ — 报告与审计（4 份）

| 文档 | 日期 | 说明 |
|:-----|:-----|:-----|
| `ARCHITECTURE_DEEP_SCAN_2026-06-21.md` | 06-21 | 架构深度扫描 v3 — 168 问题，加权 4.9/10 → 7.5/10 |
| `ARCHITECTURE_SCAN_2026-06-20.md` | 06-20 | 架构扫描 v2 — 分层审计 + 修复路线图 |
| `PERFORMANCE_BASELINE.md` | 06-16 | 性能压测基线（场景 A/B/C、瓶颈分析） |
| `PERFORMANCE_TESTING_REPORT.md` | 06-16 | 性能测试完成报告 |

---

## 📖 guides/ — 开发指南（2 份）

| 文档 | 说明 |
|:-----|:-----|
| `GIT_WORKFLOW_GUIDE.md` | Git 工作流（Trunk-Based、PR流程、提交规范） |
| `OPENAPI_MANAGEMENT.md` | OpenAPI 规范三层自动更新管理 |

---

## 📦 archive/ — 历史归档（15+ 份，不变）

> 设计阶段文档和历史报告，仅供查阅。

---

## 🗄️ 其他位置文档

| 文档 | 位置 | 说明 |
|:-----|:-----|:-----|
| `README.md` | 项目根 | 项目说明 |
| `WINDOWS_TROUBLESHOOTING_GUIDE.md` | `moling-server/` | Windows 环境排查 |
| `moling-project-structure.md` | 项目根 | 项目结构速查 |

---

## 🔗 交叉验证矩阵

| 文档 A | 文档 B | 验证内容 |
|:-------|:-------|:---------|
| `ARCHITECTURE.md` | `SPECIFICATIONS.md` | 模块划分与功能规格一致 |
| `ARCHITECTURE.md` | `DEPLOYMENT.md` | 部署架构一致性（端口、容器名、拓扑） |
| `DEPLOYMENT.md` | `operations/RUNBOOK.md` | 故障恢复与部署配置一致 |
| `DEPLOYMENT.md` | `operations/CI_CD_SETUP.md` | CI/CD 流水线与 Compose 一致 |
| `SECURITY_HARDENING.md` | `DEPLOYMENT.md` | 安全配置在部署中正确应用 |
| `SPECIFICATIONS.md` | `design/fe-specs.md` | 前后端功能边界一致 |
| `design/VIBE_WRITING_DESIGN.md` | `design/DESIGN.md` | 交互与视觉一致性 |
