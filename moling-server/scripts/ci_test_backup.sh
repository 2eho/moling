#!/bin/bash
#
# 备份脚本 CI 测试脚本
#
# 使用方法：
#   ./scripts/ci_test_backup.sh
#
# 此脚本用于在 CI 环境中测试备份、恢复和监控功能

set -e  # 遇到错误立即退出

echo "=========================================="
echo "备份脚本 CI 测试"
echo "=========================================="

# 配置
TEST_DB_NAME="moling_test"
TEST_DB_USER="postgres"
TEST_DB_PASSWORD="postgres"
TEST_DB_HOST="localhost"
TEST_DB_PORT="5432"
BACKUP_DIR="/tmp/moling_backup_test"
RESTORED_DB_NAME="moling_test_restored"

# 构建数据库 URL
DATABASE_URL="postgresql://${TEST_DB_USER}:${TEST_DB_PASSWORD}@${TEST_DB_HOST}:${TEST_DB_PORT}/${TEST_DB_NAME}"

# 创建测试目录
mkdir -p "$BACKUP_DIR"
echo "✓ 测试目录已创建: $BACKUP_DIR"

# 函数：清理测试环境
cleanup() {
    echo ""
    echo "清理测试环境..."

    # 删除恢复的数据库
    psql -h "$TEST_DB_HOST" -U "$TEST_DB_USER" -c "DROP DATABASE IF EXISTS $RESTORED_DB_NAME;" postgres || true

    # 删除测试备份
    rm -rf "$BACKUP_DIR"

    echo "✓ 清理完成"
}

# 捕获退出信号，执行清理
trap cleanup EXIT

# 检查依赖
echo ""
echo "检查依赖..."

if ! command -v python3 &> /dev/null; then
    echo "✗ 错误: 未找到 python3"
    exit 1
fi
echo "✓ Python 已安装"

if ! command -v psql &> /dev/null; then
    echo "✗ 错误: 未找到 psql"
    exit 1
fi
echo "✓ PostgreSQL 客户端已安装"

if ! command -v pg_dump &> /dev/null; then
    echo "✗ 错误: 未找到 pg_dump"
    exit 1
fi
echo "✓ pg_dump 已安装"

# 检查数据库连接
echo ""
echo "检查数据库连接..."
if ! psql -h "$TEST_DB_HOST" -U "$TEST_DB_USER" -c "SELECT 1;" "$TEST_DB_NAME" &> /dev/null; then
    echo "✗ 错误: 无法连接到数据库 $TEST_DB_NAME"
    echo "  请确保 PostgreSQL 正在运行且数据库已创建"
    exit 1
fi
echo "✓ 数据库连接正常"

# 创建测试表
echo ""
echo "创建测试数据..."
psql -h "$TEST_DB_HOST" -U "$TEST_DB_USER" -d "$TEST_DB_NAME" << EOF
CREATE TABLE IF NOT EXISTS test_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

TRUNCATE test_table;
INSERT INTO test_table (name) VALUES ('test1'), ('test2'), ('test3');
EOF
echo "✓ 测试数据已创建"

# 测试 1: 全量备份
echo ""
echo "=========================================="
echo "测试 1: 全量备份"
echo "=========================================="

python3 "$(dirname "$0")/backup_pg_dump.py" \
    --type full \
    --db-url "$DATABASE_URL" \
    --backup-dir "$BACKUP_DIR" \
    --no-cleanup

# 检查备份文件
if [ ! -f "$BACKUP_DIR"/*.sql.gz ]; then
    echo "✗ 错误: 备份文件未创建"
    exit 1
fi
echo "✓ 全量备份成功"

# 测试 2: 备份验证
echo ""
echo "=========================================="
echo "测试 2: 备份验证"
echo "=========================================="

BACKUP_FILE=$(ls "$BACKUP_DIR"/*.sql.gz | head -1)

python3 "$(dirname "$0")/backup_pg_dump.py" \
    --type full \
    --db-url "$DATABASE_URL" \
    --backup-dir "$BACKUP_DIR" \
    --verify \
    --no-cleanup

echo "✓ 备份验证成功"

# 测试 3: 灾备演练
echo ""
echo "=========================================="
echo "测试 3: 灾备演练"
echo "=========================================="

# 创建恢复的数据库
psql -h "$TEST_DB_HOST" -U "$TEST_DB_USER" -c "CREATE DATABASE $RESTORED_DB_NAME;" postgres 2>/dev/null || true

python3 "$(dirname "$0")/disaster_recovery_drill.py" \
    --db-url "$DATABASE_URL" \
    --backup-dir "$BACKUP_DIR" \
    --target-db "$RESTORED_DB_NAME" \
    --report-file "$BACKUP_DIR/drill_report.md" \
    --detailed

# 检查报告
if [ ! -f "$BACKUP_DIR/drill_report.md" ]; then
    echo "✗ 错误: 演练报告未生成"
    exit 1
fi
echo "✓ 灾备演练成功"

# 测试 4: 备份监控
echo ""
echo "=========================================="
echo "测试 4: 备份监控"
echo "=========================================="

python3 "$(dirname "$0")/monitor_backup.py" \
    --backup-dir "$BACKUP_DIR" \
    --backup-type full \
    --max-age-hours 1 \
    --quiet

echo "✓ 备份监控成功"

# 测试 5: 加密备份（如果 GPG 可用）
if command -v gpg &> /dev/null; then
    echo ""
    echo "=========================================="
    echo "测试 5: 加密备份"
    echo "=========================================="

    # 生成测试 GPG 密钥
    cat > /tmp/gpg_test_key.params <<EOF
%echo Generating test GPG key
Key-Type: RSA
Key-Length: 2048
Subkey-Type: RSA
Subkey-Length: 2048
Name-Real: CI Test
Name-Email: ci-test@example.com
Expire-Date: 0
%no-protection
%commit
%echo done
EOF

    gpg --batch --gen-key /tmp/gpg_test_key.params 2>/dev/null || true

    # 测试加密备份
    python3 "$(dirname "$0")/backup_pg_dump.py" \
        --type full \
        --db-url "$DATABASE_URL" \
        --backup-dir "$BACKUP_DIR" \
        --encrypt \
        --gpg-recipient "ci-test@example.com" \
        --no-cleanup

    # 检查加密文件
    if [ ! -f "$BACKUP_DIR"/*.sql.gz.gpg ]; then
        echo "✗ 错误: 加密备份文件未创建"
        exit 1
    fi
    echo "✓ 加密备份成功"
else
    echo ""
    echo "⚠ 跳过加密测试: GPG 未安装"
fi

# 总结
echo ""
echo "=========================================="
echo "所有测试通过！"
echo "=========================================="

exit 0
