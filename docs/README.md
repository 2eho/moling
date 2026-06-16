# 墨灵(Moling) 项目文档索引

> **文档版本**: 1.0.0  
> **最后更新**: 2026-06-16  
> **维护者**: Moling Team

---

## 📚 文档导航

欢迎来到墨灵(Moling) 项目文档中心！本文档索引帮助你快速找到需要的文档。

---

## 🚀 快速开始

| 文档 | 简介 | 适用人员 |
|------|------|----------|
| [新开发者快速上手](ONBOARDING.md) | 环境配置、依赖安装、启动开发环境 | 新开发者 |
| [部署指南](DEPLOYMENT_GUIDE.md) | 生产环境部署步骤、Docker 配置 | 运维人员、开发人员 |
| [系统架构说明](ARCHITECTURE.md) | 技术栈、架构图、数据流图 | 开发人员、架构师 |

---

## 📖 文档分类

### 1. 运维文档

| 文档 | 简介 | 最后更新 |
|------|------|----------|
| [故障处理 SOP (RUNBOOK)](RUNBOOK.md) | API 500 错误、数据库 CPU 100%、前端部署失败、SSL 证书过期等故障的处理步骤 | 2026-06-16 |
| [故障演练记录](DISASTER_RECOVERY_LOG.md) | 故障演练计划、执行记录、改进措施 | 2026-06-16 |
| [部署指南](DEPLOYMENT_GUIDE.md) | Docker 部署、CI/CD 管道、监控配置、故障排除 | 2026-06-15 |
| [部署指南 (中文)](部署指南.md) | 同上（中文版） | 2026-06-15 |
| [安全加固指南](SECURITY_HARDENING.md) | 安全配置、认证授权、防护措施 | 2026-06-16 |

### 2. 开发文档

| 文档 | 简介 | 最后更新 |
|------|------|----------|
| [新开发者快速上手](ONBOARDING.md) | 环境要求、克隆项目、安装依赖、配置环境变量、启动开发环境、运行测试、代码规范、提交规范 | 2026-06-16 |
| [系统架构说明](ARCHITECTURE.md) | 系统架构图、数据流图、技术栈说明、部署架构、第三方服务、目录结构、安全架构、性能优化 | 2026-06-16 |
| [监控配置指南](MONITORING_SETUP.md) | Prometheus + Grafana 配置、指标监控、告警规则 | 2026-06-16 |

### 3. 性能文档

| 文档 | 简介 | 最后更新 |
|------|------|----------|
| [性能基线](PERFORMANCE_BASELINE.md) | API 响应时间基线、资源使用基线 | 2026-06-16 |
| [性能测试报告](PERFORMANCE_TESTING_REPORT.md) | 负载测试、压力测试、性能优化建议 | 2026-06-16 |

### 4. 架构图表

| 文档 | 简介 | 最后更新 |
|------|------|----------|
| [类图 (Mermaid)](class-diagram.mermaid) | 系统类图（Mermaid 格式） | 2026-06-12 |
| [类图 (PlantUML)](class-diagram-genre.mermaid) | 系统类图（PlantUML 格式） | 2026-06-12 |
| [时序图 (Mermaid)](sequence-diagram.mermaid) | 用户请求时序图（Mermaid 格式） | 2026-06-12 |
| [时序图 (详细)](sequence-diagram-pipeline.mermaid) | 数据处理流水线时序图 | 2026-06-12 |
| [时序图 (Ingest)](sequence-diagram-ingest.mermaid) | 数据导入时序图 | 2026-06-12 |

### 5. 配置文件示例

| 文档 | 简介 | 最后更新 |
|------|------|----------|
| [Nginx 配置示例](moling.nginx.conf) | Nginx 反向代理配置示例 | 2026-06-15 |

---

## 🎯 按角色查找文档

### 新开发者

1. 先读：[新开发者快速上手](ONBOARDING.md)
2. 再读：[系统架构说明](ARCHITECTURE.md)
3. 参考：[代码规范](../README.md#代码规范)（在项目根目录 README.md 中）

### 后端开发人员

1. 先读：[系统架构说明](ARCHITECTURE.md)
2. 参考：[新开发者快速上手](ONBOARDING.md)（环境配置）
3. 遇到问题：[故障处理 SOP](RUNBOOK.md)

### 前端开发人员

1. 先读：[新开发者快速上手](ONBOARDING.md)
2. 参考：[系统架构说明](ARCHITECTURE.md)（前端技术栈部分）
3. 遇到问题：[故障处理 SOP](RUNBOOK.md) → 故障 3：前端部署失败

### 运维人员

1. 先读：[部署指南](DEPLOYMENT_GUIDE.md)
2. 再读：[故障处理 SOP](RUNBOOK.md)
3. 参考：[监控配置指南](MONITORING_SETUP.md)
4. 定期读：[故障演练记录](DISASTER_RECOVERY_LOG.md)

### 架构师

1. 先读：[系统架构说明](ARCHITECTURE.md)
2. 参考：[性能基线](PERFORMANCE_BASELINE.md)
3. 参考：[安全加固指南](SECURITY_HARDENING.md)

---

## 🔧 常用命令速查

### 开发环境

```bash
# 启动后端
cd moling-server && source venv/bin/activate && uvicorn app.main:app --reload

# 启动前端
cd moling-web && npm run dev

# 运行后端测试
cd moling-server && pytest

# 运行前端测试
cd moling-web && npm run test
```

### 生产环境

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f [service_name]

# 重启服务
docker-compose restart [service_name]

# 停止所有服务
docker-compose down
```

---

## 📞 获取帮助

### 团队联系方式

| 角色 | 姓名 | 邮箱 | 备注 |
|------|------|------|------|
| 技术负责人 | - | - | 请补充 |
| 后端负责人 | - | - | 请补充 |
| 前端负责人 | - | - | 请补充 |
| 运维负责人 | - | - | 请补充 |

> **注意**：请在实际使用时填写上表中的联系信息。

### 在线资源

- [项目 Git 仓库](https://github.com/[your-org]/MolingProject)（请填写实际地址）
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Next.js 官方文档](https://nextjs.org/docs)
- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [Redis 官方文档](https://redis.io/docs/)
- [Docker 官方文档](https://docs.docker.com/)

---

## 📝 文档维护

### 文档更新记录

| 日期 | 文档 | 变更内容 | 作者 |
|------|------|----------|------|
| 2026-06-16 | RUNBOOK.md | 新建文档 | Moling Team |
| 2026-06-16 | ARCHITECTURE.md | 新建文档 | Moling Team |
| 2026-06-16 | ONBOARDING.md | 新建文档 | Moling Team |
| 2026-06-16 | DISASTER_RECOVERY_LOG.md | 新建文档 | Moling Team |
| 2026-06-16 | README.md | 新建文档（本文档） | Moling Team |

### 文档维护规则

1. **版本控制**：所有文档使用 Git 进行版本控制
2. **更新频率**：
   - 运维文档（RUNBOOK、DEPLOYMENT_GUIDE）：每次变更后立即更新
   - 开发文档（ONBOARDING、ARCHITECTURE）：每季度审核一次
   - 性能文档（PERFORMANCE_*）：每次性能测试后更新
3. **审核机制**：所有文档变更需要 Code Review
4. **归档规则**：过时文档移动到 `docs/archive/` 目录

---

## 🎉 恭喜！

你已经完成了文档中心之旅！现在可以开始使用墨灵项目了。

**下一步建议**：

1. 新开发者 → 阅读 [新开发者快速上手](ONBOARDING.md)
2. 部署项目 → 阅读 [部署指南](DEPLOYMENT_GUIDE.md)
3. 了解架构 → 阅读 [系统架构说明](ARCHITECTURE.md)
4. 遇到问题 → 查阅 [故障处理 SOP](RUNBOOK.md)

---

**文档版本**: 1.0.0  
**最后更新**: 2026-06-16  
**维护者**: Moling Team

---

**END**
