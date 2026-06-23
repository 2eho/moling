#!/usr/bin/env bash
# ==============================================================================
# 自动清理 Cargo 旧版 build 缓存
# 规则: 每次 cargo build 后，同 crate 只保留最新 hash 目录，删除旧版本
# 触发: 手动运行或被 Makefile/package.json 的构建命令链式调用
# ==============================================================================
set -euo pipefail

BUILD_DIR="${1:-src-tauri/target/debug/build}"

if [ ! -d "$BUILD_DIR" ]; then
  echo "[clean-cargo-builds] $BUILD_DIR 不存在，跳过"
  exit 0
fi

cd "$BUILD_DIR"

declare -A kept
deleted=0
skipped=0

# 按修改时间倒序处理：先遇到的就是最新的
for dir in $(ls -1t 2>/dev/null); do
  [ -d "$dir" ] || continue
  # 去掉末尾 16 位 hex hash
  crate_name="${dir%-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]}"
  
  if [ -z "${kept[$crate_name]:-}" ]; then
    kept["$crate_name"]="$dir"
  else
    rm -rf "$dir"
    deleted=$((deleted + 1))
  fi
done

echo "[clean-cargo-builds] 保留 ${#kept[@]} crate，删除 $deleted 旧版本 → $(du -sh . 2>/dev/null | cut -f1 || echo 'OK')"
