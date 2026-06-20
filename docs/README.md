# 墨灵 (Moling) 文档

> **最后更新**: 2026-06-21 | **文档数量**: 3 核心 + archive/

---

## 核心文档（3 份，Agent 优化）

| 文档 | 版本 | 说明 |
|:-----|:----:|:-----|
| `ARCHITECTURE.md` | 1.5.0 | **后端架构唯一真相来源** — 系统拓扑、数据流、部署（Docker/Nginx/env）、Phase 4 状态机、Worker 可靠性链路（Celery Beat/DB会话/三层异常）、DAO 规范、AppError 体系、Windows 适配、安全加固、健康检查、常用操作命令附录 |
| `SPECIFICATIONS.md` | 2.1.0 | **功能规格唯一真相来源** — P0/P1 规格、卡牌组合算法、架构加固记录（AppError/Worker/Celery/DAO/安全/Windows/模型关系/API端点）、质量门禁 |
| `DESIGN.md` | 2.0.0 | **前端设计唯一真相来源** — 技术栈、8 主题系统、Vibe Writing 交互模型（Agent of Agents）、路由结构、状态管理（zustand/TanStack Query）、Sidebar 规则、代码规范 |

## Agent 查阅规则

- **想知道后端怎么工作的** → grep `ARCHITECTURE.md`，一个文件全覆盖
- **想知道某个功能该做成什么样** → grep `SPECIFICATIONS.md`，规格即裁判
- **想知道前端技术栈和交互模型** → grep `DESIGN.md`，一个文件看清楚
- **剩余所有文档都在 `archive/`** — agent 不需要看，人类按需查阅

---

## archive/ — 历史归档

包含：扫描报告、性能测试、运维 SOP、备份策略、入职指南、Git 规范、OpenAPI 管理等一次性/辅助文档。仅供人类查阅，agent 忽略。
