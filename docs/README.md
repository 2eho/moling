# 墨灵 (Moling) 文档索引

> **最后更新**: 2026-06-18

---

## 📋 核心文档（7 份）

| 文档 | 说明 | 适用人群 |
|:-----|:-----|:---------|
| `ARCHITECTURE.md` | 系统架构（部署拓扑、数据流、技术栈、安全架构） | 全体开发者 |
| `DEPLOYMENT.md` | 部署指南（Docker/Nginx/云服务器/故障排查） | 运维/部署 |
| `SPECIFICATIONS.md` | P0/P1/卡牌算法规格（质量门禁、测试要求） | 后端开发者 |
| `RUNBOOK.md` | 运维手册（7 种故障的 SOP 处理流程） | 运维/值班 |
| `ONBOARDING.md` | 新开发者上手指南（环境搭建、代码规范） | 新加入开发者 |
| `SECURITY_HARDENING.md` | 安全加固（Rate Limiting/JWT黑名单/HTTPS/CSP/SQL注入） | 安全/运维 |
| `GIT_WORKFLOW_GUIDE.md` | Git 工作流指南（Trunk-Based、PR流程、提交规范） | 全体开发者 |

## 🎨 根目录设计文档

| 文档 | 位置 | 说明 |
|:-----|:-----|:-----|
| `DESIGN.md` | 项目根目录 | 设计系统 v3.1（暗色主题、色阶、排版、组件样式） |
| `fe-specs.md` | 项目根目录 | 前端 Phase 4 & 健康监控生产级规格 |

## 📊 辅助文档

| 文档 | 说明 |
|:-----|:-----|
| `MONITORING_SETUP.md` | Sentry 监控接入配置（前后端） |
| `PERFORMANCE_BASELINE.md` | 性能压测基线（场景 A/B/C、瓶颈分析、改进建议） |
| `PERFORMANCE_TESTING_REPORT.md` | 性能测试完成报告 |
| `DISASTER_RECOVERY_LOG.md` | 灾备演练记录（数据库停止模拟） |
| `BACKUP_STRATEGY.md` | 数据库备份与灾备策略 |
| `OPENAPI_MANAGEMENT.md` | OpenAPI 规范三层自动更新管理方案 |

## 🗄️ moling-server 内部文档

| 文档 | 位置 | 说明 |
|:-----|:-----|:-----|
| `WINDOWS_TROUBLESHOOTING_GUIDE.md` | `moling-server/` | Windows 环境下常见问题排查 |

## 📦 归档文档（`archive/`）

> 设计阶段文档和历史报告，仅供查阅：

| 文档 | 说明 |
|:-----|:-----|
| `009_2b7b5b03_moling-card-combination-algorithm.md` | 卡牌组合算法设计蓝图 (217KB) |
| `012_a7c27b64_墨灵后端设计文档.md` | 后端完整设计文档 (789KB) |
| `015_54298a88_前后端接口映射.md` | 前后端接口映射文档 (46KB) |
| `016_墨灵前后端集成测试方案.md` | 集成测试方案 (30KB) |
| `API对齐报告_2026-06-16.md` | 前后端 API 对齐工作记录 |
| `前端优化报告_2026-06-15.md` | 前端性能优化实施记录 |
| `稳定专业可靠达标报告_2026-06-16.md` | P0/P1/P2 达标工程记录 |
| `统一审计报告_墨灵全项目.md` | 全项目代码审计报告 |
| `OPENAPI管理报告.md` | OpenAPI 管理实施报告 |
| `文档整理执行报告_2026-06-17.md` | 上次文档整理记录 |
| `前端UI设计审计与优化报告.md` | UI 设计审计 (2026-06-18) |
| `bandit-report.html` | Python 安全扫描报告 |

---

## 交叉验证说明

核心 7 份文档之间互为补充，无重复内容：

| 文档 | 与谁交叉验证 | 验证内容 |
|:-----|:------------|:---------|
| `ARCHITECTURE.md` | `DEPLOYMENT.md` | 部署架构一致性（端口、容器名、网络拓扑） |
| `ARCHITECTURE.md` | `SPECIFICATIONS.md` | 模块划分与功能规格一致性 |
| `DEPLOYMENT.md` | `RUNBOOK.md` | 故障恢复路径与部署配置一致 |
| `DEPLOYMENT.md` | `SECURITY_HARDENING.md` | 安全配置在部署中正确应用 |
| `SPECIFICATIONS.md` | `fe-specs.md` | 前后端功能边界一致 |
| `GIT_WORKFLOW_GUIDE.md` | `ONBOARDING.md` | 开发流程在入职指南中体现 |
