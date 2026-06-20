#!/bin/bash
# docs/ 激进归档 — Agent 优化版
# 执行: bash docs/archive-all.sh
# 结果: docs/ 只保留 3 份核心文档 + archive/

set -e
DOCS="docs"
ARCHIVE="$DOCS/archive"

echo "=== 激进归档：41 文档 → 3 核心 + archive ==="

# 1. 前面做好的设计子目录（如果有），先清理
rm -rf "$DOCS/design" "$DOCS/operations" "$DOCS/reports" "$DOCS/guides" 2>/dev/null || true

# 2. 全部辅助文档 → archive/
mv "$DOCS/DEPLOYMENT.md"               "$ARCHIVE/"  2>/dev/null || true
mv "$DOCS/SECURITY_HARDENING.md"       "$ARCHIVE/"  2>/dev/null || true
mv "$DOCS/ONBOARDING.md"               "$ARCHIVE/"  2>/dev/null || true
mv "$DOCS/RUNBOOK.md"                  "$ARCHIVE/"  2>/dev/null || true
mv "$DOCS/BACKUP_STRATEGY.md"          "$ARCHIVE/"  2>/dev/null || true
mv "$DOCS/DISASTER_RECOVERY_LOG.md"    "$ARCHIVE/"  2>/dev/null || true
mv "$DOCS/MONITORING_SETUP.md"         "$ARCHIVE/"  2>/dev/null || true
mv "$DOCS/CI_CD_SETUP.md"              "$ARCHIVE/"  2>/dev/null || true
mv "$DOCS/GIT_WORKFLOW_GUIDE.md"       "$ARCHIVE/"  2>/dev/null || true
mv "$DOCS/PERFORMANCE_BASELINE.md"     "$ARCHIVE/"  2>/dev/null || true
mv "$DOCS/PERFORMANCE_TESTING_REPORT.md" "$ARCHIVE/" 2>/dev/null || true
mv "$DOCS/design-decisions.md"         "$ARCHIVE/"  2>/dev/null || true
mv "$DOCS/前端重建方案.md"             "$ARCHIVE/"  2>/dev/null || true
mv "$DOCS/ARCHITECTURE_SCAN_2026-06-20.md"      "$ARCHIVE/" 2>/dev/null || true
mv "$DOCS/ARCHITECTURE_DEEP_SCAN_2026-06-21.md" "$ARCHIVE/" 2>/dev/null || true
mv "$DOCS/OPENAPI_MANAGEMENT.md"       "$ARCHIVE/"  2>/dev/null || true
mv "$DOCS/migrate-docs.sh"             "$ARCHIVE/"  2>/dev/null || true

# 3. 根目录清理
rm -f "overview.md"
rm -f "moling-project-structure.md"
# fe-specs.md / OPENAPI_MANAGEMENT.md → archive
mv "fe-specs.md"                       "$ARCHIVE/"  2>/dev/null || true
mv "OPENAPI_MANAGEMENT.md"             "$ARCHIVE/"  2>/dev/null || true

# 4. DESIGN.md 保留在 docs/，VIBE_WRITING 移入 archive（如需则手动合并入 DESIGN）
mv "VIBE_WRITING_DESIGN.md"            "$ARCHIVE/"  2>/dev/null || true
mv "DESIGN.md"                         "$ARCHIVE/"  2>/dev/null || true

echo ""
echo "=== 归档完成 ==="
echo "docs/ 剩余文件:"
ls -la "$DOCS/"*.md 2>/dev/null
echo ""
echo "核心 3 文档:"
echo "  docs/ARCHITECTURE.md     — 全部后端架构 + 操作命令"
echo "  docs/SPECIFICATIONS.md   — 全部功能规格 + 质量门禁"
echo "  docs/DESIGN.md           — 全部前端设计 (需手动合并 VIBE_WRITING/design-decisions)"
echo ""
echo "其余全部在 archive/，agent 不会查阅。"
