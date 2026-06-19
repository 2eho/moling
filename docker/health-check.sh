#!/bin/bash
# ==============================================================================
# 墨灵 Moling — 服务器端健康检查脚本
# ==============================================================================
# 用途: 全面检查墨灵所有服务的健康状态
# 调用: ./health-check.sh [--verbose] [--json]
#
# 检查项:
#   1. Docker 守护进程状态
#   2. 容器运行状态 (app / frontend / worker / db / redis)
#   3. 后端 API 健康端点
#   4. 前端页面可达性
#   5. 数据库连接
#   6. Redis 连接
#   7. 磁盘空间
#   8. 内存使用
# ==============================================================================

set -euo pipefail

# ---- 配置 ----
BASE_URL="${BASE_URL:-http://localhost:8080}"
VERBOSE=false
OUTPUT_JSON=false

# ---- 颜色 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ---- 解析参数 ----
for arg in "$@"; do
    case $arg in
        --verbose) VERBOSE=true ;;
        --json)    OUTPUT_JSON=true ;;
    esac
done

# ---- 计数器 ----
PASS=0
FAIL=0
WARN=0

# ---- 辅助函数 ----
pass() { PASS=$((PASS+1)); [ "$VERBOSE" = true ] && echo -e "  ${GREEN}✅${NC} $1"; }
fail() { FAIL=$((FAIL+1)); echo -e "  ${RED}❌${NC} $1"; }
warn() { WARN=$((WARN+1)); echo -e "  ${YELLOW}⚠️${NC}  $1"; }
check() {
    local name="$1" url="$2" expected="${3:-200}"
    if curl -sf -o /dev/null -w "%{http_code}" --max-time 10 "${url}" 2>/dev/null | grep -q "${expected}"; then
        pass "$name ($(curl -s -o /dev/null -w '%{time_total}' --max-time 10 "${url}" 2>/dev/null)s)"
    else
        fail "$name"
    fi
}

echo "========================================="
echo "  Moling 健康检查"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="
echo ""

# ---- 1. Docker 守护进程 ----
echo "┌─ Docker 守护进程 ──────────────────────┐"
if docker info > /dev/null 2>&1; then
    pass "Docker 运行中"
else
    fail "Docker 未运行"
fi

# ---- 2. 容器状态 ----
echo "├─ 容器状态 ─────────────────────────────┤"
for svc in moling-db moling-redis moling-api moling-worker moling-frontend; do
    STATUS=$(docker inspect -f '{{.State.Status}}' "${svc}" 2>/dev/null || echo "missing")
    HEALTH=$(docker inspect -f '{{.State.Health.Status}}' "${svc}" 2>/dev/null || echo "N/A")
    case "${STATUS}" in
        running)
            if [ "${HEALTH}" = "healthy" ]; then
                pass "${svc} (运行中, 健康)"
            elif [ "${HEALTH}" = "N/A" ]; then
                pass "${svc} (运行中)"
            else
                warn "${svc} (运行中, 健康: ${HEALTH})"
            fi
            ;;
        missing)
            warn "${svc} (未部署)"
            ;;
        *)
            fail "${svc} (状态: ${STATUS})"
            ;;
    esac
done

# ---- 3. HTTP 端点 ----
echo "├─ HTTP 端点 ────────────────────────────┤"
check "根路径重定向"  "${BASE_URL}/"                        "301"
check "前端页面"      "${BASE_URL}/moling"                  "20"
check "API 健康检查"  "${BASE_URL}/moling/api/v1/health"     "200"
check "API 文档"      "${BASE_URL}/moling/api/v1/docs"       "200"
check "OpenAPI JSON"  "${BASE_URL}/moling/api/v1/openapi.json" "200"

# ---- 4. 系统资源 ----
echo "├─ 系统资源 ─────────────────────────────┤"

# 磁盘
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "${DISK_USAGE}" -gt 90 ]; then
    fail "磁盘使用率: ${DISK_USAGE}% (严重)"
elif [ "${DISK_USAGE}" -gt 80 ]; then
    warn "磁盘使用率: ${DISK_USAGE}% (偏高)"
else
    pass "磁盘使用率: ${DISK_USAGE}%"
fi

# 内存
MEM_TOTAL=$(free -m | awk 'NR==2 {print $2}')
MEM_USED=$(free -m | awk 'NR==2 {print $3}')
MEM_PCT=$((MEM_USED * 100 / MEM_TOTAL))
if [ "${MEM_PCT}" -gt 90 ]; then
    fail "内存使用率: ${MEM_PCT}% (${MEM_USED}M/${MEM_TOTAL}M)"
elif [ "${MEM_PCT}" -gt 80 ]; then
    warn "内存使用率: ${MEM_PCT}% (${MEM_USED}M/${MEM_TOTAL}M)"
else
    pass "内存使用率: ${MEM_PCT}% (${MEM_USED}M/${MEM_TOTAL}M)"
fi

# Docker 磁盘
DOCKER_DISK=$(docker system df --format '{{.TotalCount}} images, {{.Size}}' 2>/dev/null || echo "N/A")
pass "Docker 资源: ${DOCKER_DISK}"

# ---- 5. 数据库连接 ----
echo "├─ 数据库 ───────────────────────────────┤"
if docker exec moling-db pg_isready -U moling -d moling > /dev/null 2>&1; then
    pass "PostgreSQL 连接正常"
else
    fail "PostgreSQL 连接失败"
fi

# ---- 6. Redis 连接 ----
if docker exec moling-redis redis-cli -a "${REDIS_PASSWORD:-moling_redis_password}" ping 2>/dev/null | grep -q "PONG"; then
    pass "Redis 连接正常"
else
    fail "Redis 连接失败"
fi

# ---- 汇总 ----
echo "└────────────────────────────────────────┘"
echo ""
echo "========================================="
TOTAL=$((PASS + FAIL + WARN))
if [ "${FAIL}" -eq 0 ] && [ "${WARN}" -eq 0 ]; then
    echo -e "  ${GREEN}全部通过 ✅  (${PASS}/${TOTAL})${NC}"
elif [ "${FAIL}" -eq 0 ]; then
    echo -e "  ${YELLOW}有警告 ⚠️  (通过:${PASS} 警告:${WARN}/${TOTAL})${NC}"
else
    echo -e "  ${RED}有问题 ❌  (通过:${PASS} 失败:${FAIL} 警告:${WARN}/${TOTAL})${NC}"
fi
echo "========================================="

# JSON 输出
if [ "${OUTPUT_JSON}" = true ]; then
    echo ""
    echo "{"
    echo "  \"timestamp\": \"$(date -Iseconds)\","
    echo "  \"passed\": ${PASS},"
    echo "  \"failed\": ${FAIL},"
    echo "  \"warnings\": ${WARN},"
    echo "  \"healthy\": $([ "${FAIL}" -eq 0 ] && echo "true" || echo "false")"
    echo "}"
fi

exit "${FAIL}"
