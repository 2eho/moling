#!/bin/bash
# =============================================================================
# 墨灵一键部署脚本
# =============================================================================
# 用法:
#   1. 编辑项目根目录 .env 文件填入服务器 IP / 域名
#   2. ./deploy.sh
# =============================================================================
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "=========================================="
echo "  墨灵 (Moling) 一键部署"
echo "=========================================="

# 1. 检查 .env 是否存在
if [ ! -f .env ]; then
    echo "[ERROR] 根目录 .env 文件不存在！"
    echo "  请先创建 .env（可参考下面的模板）："
    echo "  SERVER_IP=你的服务器IP"
    echo "  FRONTEND_URL=http://你的服务器IP:8080"
    echo "  BACKEND_API_URL=http://你的服务器IP:8000/api/v1"
    exit 1
fi

# 2. 检查是否还是占位值
if grep -q "YOUR_SERVER_IP" .env; then
    echo "[ERROR] .env 中仍有占位符 YOUR_SERVER_IP，请替换为实际 IP 或域名！"
    exit 1
fi

echo "[1/3] 构建并启动所有服务..."
docker compose up -d --build

echo "[2/3] 等待服务就绪（约 30 秒）..."
sleep 10

# 3. 健康检查
echo "[3/3] 健康检查..."
for i in 1 2 3; do
    if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo "  [OK] 后端 API 健康 ✓"
        break
    fi
    if [ "$i" = "3" ]; then
        echo "  [WARN] 后端健康检查未通过，请检查: docker compose logs app"
    fi
    sleep 5
done

# 读取 .env 中的变量用于显示
source .env 2>/dev/null || true

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo "  前端地址:   ${FRONTEND_URL:-http://localhost:8080}"
echo "  后端 API:   http://localhost:8000/api/v1"
echo "  API 文档:   http://localhost:8000/docs"
echo ""
echo "  日志查看:   docker compose logs -f"
echo "  重新部署:   ./deploy.sh"
echo "  停止服务:   docker compose down"
echo "=========================================="
