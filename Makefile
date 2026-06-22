# ==============================================================================
# 墨灵 Moling — 运维 Makefile
# ==============================================================================
# 提供常用运维操作的快捷命令，本地开发和生产服务器通用。
#
# 用法:
#   make help          — 显示所有可用命令
#   make dev           — 启动开发环境
#   make prod          — 启动生产环境
#   make deploy        — 从 GHCR 拉取并部署
#   make health        — 运行健康检查
#   make backup        — 备份数据库
#   make logs          — 查看所有服务日志
# ==============================================================================

.PHONY: help dev prod deploy health backup logs clean restart status

# ---- 默认目标 ----
help:
	@echo "========================================="
	@echo "  Moling 运维命令"
	@echo "========================================="
	@echo ""
	@echo "  make dev         启动开发环境（含端口映射）"
	@echo "  make prod        启动生产环境（从 GHCR 拉取）"
	@echo "  make prod-build  本地构建并启动生产环境"
	@echo "  make deploy      拉取最新镜像并滚动更新"
	@echo ""
	@echo "  make health      运行全面健康检查"
	@echo "  make status      查看所有容器状态"
	@echo "  make logs        查看所有服务日志（tail -f）"
	@echo "  make logs-server 只看后端日志"
	@echo ""
	@echo "  make backup      备份数据库"
	@echo "  make restart     重启所有服务"
	@echo "  make clean       停止并清理所有容器"
	@echo "  make prune       清理未使用的镜像和卷"
	@echo ""

# ---- 环境启动 ----
dev:
	@echo "🚀 启动开发环境..."
	docker compose -f docker-compose.yml up -d --build
	@echo "✅ 开发环境已启动"
	@echo "   前端: http://localhost:3000/moling"
	@echo "   后端: http://localhost:8000/health"

prod:
	@echo "🚀 启动生产环境（GHCR 镜像）..."
	cd docker && docker compose -f docker-compose.prod.yml pull
	cd docker && docker compose -f docker-compose.prod.yml up -d
	@echo "✅ 生产环境已启动"

prod-build:
	@echo "🔨 本地构建并启动生产环境..."
	cd docker && docker compose -f docker-compose.yml up -d --build
	@echo "✅ 生产环境已启动（本地构建）"

prod-monitoring:
	@echo "📊 启动生产环境 + 监控栈..."
	cd docker && docker compose -f docker-compose.prod.yml --profile monitoring up -d
	@echo "✅ 全部服务已启动"
	@echo "   Prometheus: http://localhost:9090"
	@echo "   Grafana:    http://localhost:3001"

# ---- 部署 ----
deploy:
	@echo "📦 拉取最新镜像并滚动更新..."
	cd docker && docker compose -f docker-compose.prod.yml pull app frontend worker
	cd docker && docker compose -f docker-compose.prod.yml up -d --no-deps app frontend worker
	@echo "✅ 滚动更新完成"

# ---- 监控和状态 ----
health:
	bash docker/health-check.sh --verbose

status:
	@echo "📋 容器状态:"
	@cd docker && docker compose -f docker-compose.prod.yml ps 2>/dev/null || docker compose -f docker-compose.yml ps

logs:
	cd docker && docker compose -f docker-compose.prod.yml logs -f --tail=100 2>/dev/null || docker compose -f docker-compose.yml logs -f --tail=100

logs-server:
	docker logs -f --tail=100 moling-server 2>/dev/null

logs-frontend:
	docker logs -f --tail=100 moling-frontend 2>/dev/null || docker logs -f --tail=100 moling-web

# ---- 备份 ----
backup:
	@echo "💾 备份数据库..."
	@mkdir -p docker/backups
	docker exec moling-db pg_dump -U moling moling > docker/backups/moling_db_$(shell date +%Y%m%d_%H%M%S).sql 2>/dev/null \
		|| echo "⚠️  PostgreSQL 备份失败（可能使用的是 SQLite）"
	@echo "✅ 备份完成"

# ---- 运维 ----
restart:
	@echo "🔄 重启所有服务..."
	cd docker && docker compose -f docker-compose.prod.yml restart 2>/dev/null \
		|| docker compose -f docker-compose.yml restart
	@echo "✅ 重启完成"

clean:
	@echo "🧹 停止并清理容器..."
	cd docker && docker compose -f docker-compose.prod.yml down 2>/dev/null \
		|| docker compose -f docker-compose.yml down
	@echo "✅ 清理完成"

clean-all:
	@echo "⚠️  彻底清理（含数据卷）..."
	cd docker && docker compose -f docker-compose.prod.yml down -v --remove-orphans 2>/dev/null \
		|| docker compose -f docker-compose.yml down -v --remove-orphans
	@echo "✅ 彻底清理完成"

prune:
	@echo "🗑️  清理未使用的 Docker 资源..."
	docker system prune -af --filter "until=72h"
	@echo "✅ 清理完成"

# ---- 数据库迁移 ----
migrate:
	@echo "🔧 运行数据库迁移..."
	cd docker && docker compose -f docker-compose.prod.yml run --rm app alembic upgrade head 2>/dev/null \
		|| docker compose -f docker-compose.yml run --rm app alembic upgrade head
	@echo "✅ 迁移完成"

migrate-rollback:
	@echo "⏪ 回滚数据库迁移..."
	cd docker && docker compose -f docker-compose.prod.yml run --rm app alembic downgrade -1 2>/dev/null \
		|| docker compose -f docker-compose.yml run --rm app alembic downgrade -1
	@echo "✅ 回滚完成"
