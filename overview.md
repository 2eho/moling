# 墨灵 Moling — CI/CD 自动化部署方案

## 交付摘要

为墨灵项目建立了一套完整的自动化 CI/CD 流水线，实现从代码推送到生产部署的全自动化。

## 核心变化

| 之前 | 之后 |
|------|------|
| 手工 SSH + docker-compose build | `git push main` 自动部署 |
| Docker 镜像仅手动构建 | GitHub Actions 自动构建 + 推送到 GHCR |
| 无回滚机制 | 部署失败自动回滚到上一版本 |
| 无健康检查 | 部署后冒烟测试 + 容器健康检查 |
| 手工配置 Nginx | 安全加固版配置（速率限制/安全头/Gzip） |

## 新增/修改文件

### 流水线核心
- `.github/workflows/deploy.yml` — 主部署流水线（7 Job：准备 Lint 测试 构建 部署 验证 回滚）
- `docker/docker-compose.prod.yml` — 生产编排（GHCR 预构建镜像，资源限制，日志轮转）
- `docker/deploy-remote.sh` — 远程部署脚本（CI/CD 在服务器端调用）

### 运维工具
- `Makefile` — 一键运维命令（make dev/prod/deploy/health/backup/logs）
- `docker/health-check.sh` — 全面健康检查脚本
- `scripts/server-setup.sh` — 新服务器一键初始化（Docker+Nginx+防火墙+密钥）

### 配置增强
- `deploy/nginx/moling.conf` — 增强安全版（速率限制/CSP/HSTS/Gzip/静态缓存）
- `docs/CI_CD_SETUP.md` — GitHub Secrets 配置指南

## 流水线架构

```
git push main
    │
    ▼
[prepare]  生成版本号/环境标识
    │
    ├──► [lint]      Flake8 + Bandit + Safety
    │
    ▼
[test]      后端 pytest + 前端构建 + TypeScript 检查
    │
    ▼
[build]     Docker 多平台镜像 ghcr.io/2eho/moling/*:latest
    │
    ▼
[deploy]    SSH 远程部署 滚动更新 健康检查
    │
    成功 [verify]  冒烟测试 记录报告
    │
    失败 [rollback] 自动回滚上一版本
```

## 服务器部署命令

```bash
# 初始化新服务器
bash scripts/server-setup.sh

# 日常运维
make prod          # 启动生产环境
make deploy        # 滚动更新
make health        # 健康检查
make backup        # 数据库备份
make logs          # 查看日志
```

## 下一步

1. 在 GitHub 仓库配置 Secrets（参考 docs/CI_CD_SETUP.md）
2. 在服务器运行 scripts/server-setup.sh 初始化环境
3. 推送代码到 main 分支触发首次自动部署
4. 配置监控告警（Prometheus + Grafana，make prod-monitoring）
