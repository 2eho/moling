#!/bin/bash
# docs/ 归类整合迁移脚本
# 执行: bash docs/migrate-docs.sh
# 将散落的 20+ 文档归类到 5 个子目录 + 5 核心平铺

DOCS="docs"

echo "=== 创建子目录 ==="
mkdir -p "$DOCS/design" "$DOCS/operations" "$DOCS/reports" "$DOCS/guides"

echo "=== 设计文档 → design/ ==="
mv "$DOCS/design-decisions.md"     "$DOCS/design/"
mv "$DOCS/前端重建方案.md"         "$DOCS/design/"
mv "VIBE_WRITING_DESIGN.md"        "$DOCS/design/"
mv "DESIGN.md"                     "$DOCS/design/"
mv "fe-specs.md"                   "$DOCS/design/"

echo "=== 运维文档 → operations/ ==="
mv "$DOCS/RUNBOOK.md"              "$DOCS/operations/"
mv "$DOCS/BACKUP_STRATEGY.md"      "$DOCS/operations/"
mv "$DOCS/DISASTER_RECOVERY_LOG.md" "$DOCS/operations/"
mv "$DOCS/MONITORING_SETUP.md"     "$DOCS/operations/"
mv "$DOCS/CI_CD_SETUP.md"          "$DOCS/operations/"

echo "=== 报告审计 → reports/ ==="
mv "$DOCS/ARCHITECTURE_DEEP_SCAN_2026-06-21.md" "$DOCS/reports/"
mv "$DOCS/ARCHITECTURE_SCAN_2026-06-20.md"      "$DOCS/reports/"
mv "$DOCS/PERFORMANCE_BASELINE.md"              "$DOCS/reports/"
mv "$DOCS/PERFORMANCE_TESTING_REPORT.md"        "$DOCS/reports/"

echo "=== 开发指南 → guides/ ==="
mv "$DOCS/GIT_WORKFLOW_GUIDE.md"    "$DOCS/guides/"
mv "OPENAPI_MANAGEMENT.md"          "$DOCS/guides/"

echo "=== 根目录清理 ==="
rm -f "overview.md"
# moling-project-structure.md 保留在根目录作为快速参考

echo "=== 完成 ==="
echo ""
echo "新结构:"
echo "  docs/"
echo "    ├── README.md"
echo "    ├── ARCHITECTURE.md"
echo "    ├── SPECIFICATIONS.md"
echo "    ├── DEPLOYMENT.md"
echo "    ├── SECURITY_HARDENING.md"
echo "    ├── ONBOARDING.md"
echo "    ├── design/         (5 文件)"
echo "    ├── operations/     (5 文件)"
echo "    ├── reports/        (4 文件)"
echo "    ├── guides/         (2 文件)"
echo "    └── archive/        (15+ 文件,不变)"
echo ""
echo "核心文档从 20 → 5 平铺, 总分类从 0 → 5 子目录"
