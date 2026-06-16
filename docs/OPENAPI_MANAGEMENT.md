# 墨灵项目 OpenAPI 规范管理指南

> 版本：1.0 | 最后更新：2026-06-17 | 状态：✅ 已实施

---

## 一、概述

本文档说明墨灵项目前后端共用的 OpenAPI 3.0.3 规范管理方案。

**规范文件位置**：`openapi.json`（项目根目录）

---

## 二、三层自动更新架构

### Layer 1：开发时自动保存（已实施 ✅）

**文件**：`moling-server/app/main.py`

```python
if os.getenv("ENV", "dev") == "dev":
    @app.on_event("startup")
    async def save_openapi():
        with open("openapi.json", "w", encoding="utf-8") as f:
            json.dump(app.openapi(), f, ensure_ascii=False, indent=2)
```

**效果**：后端以开发模式启动时，自动保存 `openapi.json` 到项目根目录。

---

### Layer 2：Pre-commit Hook 检查（已实施 ✅）

**文件**：`.githooks/pre-commit`

```bash
#!/bin/bash
cd moling-server || exit 1
python scripts/generate_openapi_from_doc.py ../openapi.json
if ! git diff --quiet ../openapi.json; then
    echo "⚠️  OpenAPI spec updated. Committing..."
    git add ../openapi.json
fi
```

**启用方法**：
```bash
git config core.hooksPath .githooks
```

---

### Layer 3：GitHub Actions 自动更新（已实施 ✅）

**文件**：`.github/workflows/auto-update-openapi.yml`

**触发条件**：
- Push 到 `main` 分支
- 修改了 `moling-server/app/**` 或 `moling-server/pyproject.toml`

**流程**：
1. 运行 `generate_openapi_from_doc.py` 生成最新 `openapi.json`
2. 如果内容有变化，自动 commit 并 push 到 `main`

---

## 三、使用指南

### 前端开发者

```bash
# 1. 获取最新 openapi.json
git pull

# 2. 生成 TypeScript 类型（推荐）
npx openapi-typescript openapi.json -o src/types/api.ts

# 3. 导入 Postman / Insomnia
# 直接导入 openapi.json 即可
```

### 后端开发者

```bash
# 1. 启动后端（开发模式）
cd moling-server
uvicorn app.main:app --reload

# 2. openapi.json 会自动更新到项目根目录

# 3. 提交前检查
git status  # 查看 openapi.json 是否有变化
```

### 手动生成 openapi.json

```bash
# 方法1：从运行中的后端导出
cd moling-server
python scripts/export_openapi.py

# 方法2：从无依赖脚本生成（推荐 CI 使用）
cd moling-server
python scripts/generate_openapi_from_doc.py ../openapi.json
```

---

## 四、检查与验证

### 本地检查

```bash
# 检查 openapi.json 是否与代码同步
cd moling-server
python scripts/generate_openapi_from_doc.py ../openapi.json
git diff ../openapi.json  # 应该没有差异
```

### CI 检查

`.github/workflows/openapi-check.yml` 会在每次 PR 时自动检查 `openapi.json` 是否最新。

---

## 五、文件清单

| 文件 | 说明 |
|:-----|:-----|
| `openapi.json` | OpenAPI 3.0.3 规范（前后端共用） |
| `moling-server/app/main.py` | 开发模式自动保存逻辑 |
| `moling-server/scripts/export_openapi.py` | 从运行中后端导出 |
| `moling-server/scripts/generate_openapi_from_doc.py` | 从无依赖脚本生成 |
| `.githooks/pre-commit` | Pre-commit 检查 hook |
| `.github/workflows/auto-update-openapi.yml` | GitHub Actions 自动更新 |
| `.github/workflows/openapi-check.yml` | GitHub Actions 规范检查 |

---

## 六、常见问题

### Q1：openapi.json 应该提交到 Git 吗？

**A**：✅ 应该。它是前后端共用的接口契约文件，提交后前端可以直接使用。

### Q2：为什么不用 requirements.txt？

**A**：`moling-server` 使用 `pyproject.toml` 管理依赖，`requirements.txt` 不存在。CI 中改用 `pip install ".[dev]"`。

### Q3：如何确保 openapi.json 始终最新？

**A**：三层架构保证：
1. 开发时自动保存（Layer 1）
2. Commit 前检查（Layer 2）
3. Push 后 CI 自动更新（Layer 3）

---

*文档结束*
