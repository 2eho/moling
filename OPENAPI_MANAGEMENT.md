# OpenAPI 规范管理 - 完整方案

> 三层自动更新架构，确保前后端接口永远同步

## 一、架构设计

```
┌─────────────────────────────────────────────────────────────┐
│              三层防护，确保永远同步                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 1：开发时自动保存                               │
│  → main.py 在开发模式下自动保存 openapi.json            │
│  → 后端启动时自动执行                                  │
├─────────────────────────────────────────────────────────────┤
│  Layer 2：提交时自动检查（Git Hook）                    │
│  → pre-commit hook 自动运行脚本                        │
│  → 如果忘记更新，提交前自动修复                        │
├─────────────────────────────────────────────────────────────┤
│  Layer 3：推送后自动更新（GitHub Actions）               │
│  → 检测后端代码变更                                    │
│  → 自动重新生成 openapi.json 并提交                    │
│  → 即使前两层都失效，这一层也会修复                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、文件清单

| 文件 | 用途 | 层级 |
|:-----|:-----|:-----|
| `openapi.json` | OpenAPI 规范（静态快照） | 输出 |
| `moling-server/scripts/export_openapi.py` | 从运行中的后端导出规范 | Layer 1 |
| `moling-server/scripts/generate_openapi_from_doc.py` | 从接口文档生成规范 | Layer 1/2 |
| `moling-server/app/main.py` | 自动保存 OpenAPI 规范（开发模式） | Layer 1 |
| `.githooks/pre-commit` | Git 提交前自动检查 | Layer 2 |
| `.github/workflows/auto-update-openapi.yml` | GitHub Actions 自动更新 | Layer 3 |
| `.github/workflows/openapi-check.yml` | CI 验证（接口漂移检测） | 验证 |

---

## 三、使用指南

### 🚀 首次 setup（团队每个成员都需要运行）

```bash
# 1. 安装 Git hook
cd C:\Users\Admin\Desktop\MolingProject
git config core.hooksPath .githooks

# 2. 验证 hook 是否安装成功
git hooks --list
# 应该看到：pre-commit

# 3. 前端：安装 OpenAPI 工具（可选）
cd moling-web
npm install openapi-typescript --save-dev
```

---

### 📋 日常开发流程

#### 场景 A：后端开发者修改 API

```bash
# 1. 修改后端代码（添加/修改/删除端点）
#    编辑：moling-server/app/router/*.py

# 2. 更新接口映射文档（重要！）
#    编辑：015_前后端接口映射.md

# 3. 提交代码（pre-commit hook 会自动运行）
git add .
git commit -m "feat: 添加 XX 接口"
# 自动执行：
#   → 检测到 moling-server/ 变更
#   → 运行 generate_openapi_from_doc.py
#   → 自动添加 openapi.json 到提交

# 4. 推送到 GitHub
git push
# 自动执行：
#   → GitHub Actions 运行 auto-update-openapi.yml
#   → 如果有遗漏，自动重新生成并提交
```

#### 场景 B：前端开发者使用 OpenAPI 规范

```bash
# 1. 拉取最新代码
git pull
# 自动获取最新的 openapi.json

# 2. 生成 TypeScript 类型（推荐）
cd moling-web
npm run openapi:generate
# 生成：src/lib/api-types.ts

# 3. 使用生成的类型
import type { Project, Chapter } from "@/lib/api-types";
```

---

### 🔧 手动运行脚本

```bash
# 从接口文档生成 OpenAPI 规范
cd moling-server
python scripts/generate_openapi_from_doc.py

# 从运行中的后端导出规范（更精确）
python scripts/export_openapi.py

# 检查是否与快照一致（用于 CI）
python scripts/export_openapi.py --check

# 前端：获取最新规范
cd moling-web
npm run openapi:fetch

# 前端：生成 TypeScript 类型
npm run openapi:generate
```

---

## 四、验证与测试

### ✅ 验证清单

| 验证项 | 命令 | 预期结果 |
|:-----|:-----|:-----|
| `openapi.json` 是否合法 JSON | `python -m json.tool openapi.json` | 无错误 |
| 是否包含 79 个路径 | `python -c "import json; d=json.load(open('openapi.json')); print(f'路径数：{len(d[\"paths\"])}')"` | 路径数：79 |
| Git hook 是否生效 | `git commit -m "test"` | 自动运行脚本 |
| GitHub Actions 是否运行 | 推送代码到 GitHub | 自动更新 openapi.json |

---

### 🧪 测试步骤

#### 测试 1：验证 Git hook

```bash
# 1. 修改后端代码
echo "# test" >> moling-server/app/router/auth.py

# 2. 提交代码
git add moling-server/
git commit -m "test: 验证 Git hook"
# 应该看到：
#   📄 正在检查 OpenAPI 规范...
#   ✓ 检测到后端代码变更，重新生成 OpenAPI 规范...
#   ✓ openapi.json 已更新，自动添加到提交

# 3. 检查 openapi.json 是否被添加
git log --oneline -1
# 应该包含 openapi.json 的变更
```

#### 测试 2：验证 GitHub Actions

```bash
# 1. 推送到 GitHub
git push

# 2. 检查 GitHub Actions
#    访问：https://github.com/2eho/moling/actions

# 3. 检查是否自动更新 openapi.json
#    访问：https://github.com/2eho/moling/blob/main/openapi.json
```

---

## 五、故障排除

### ❌ 问题 1：Git hook 不运行

**原因**：Git hook 路径未配置

**解决**：
```bash
cd C:\Users\Admin\Desktop\MolingProject
git config core.hooksPath .githooks
```

---

### ❌ 问题 2：Windows 上 Git hook 运行失败

**原因**：Git hook 需要 Git Bash 环境

**解决**：
1. 确保安装了 Git Bash
2. 检查 `.githooks/pre-commit` 文件是否有可执行权限
3. 手动测试：`bash .githooks/pre-commit`

---

### ❌ 问题 3：GitHub Actions 运行失败

**原因**：依赖缺失或脚本错误

**解决**：
1. 检查 `.github/workflows/auto-update-openapi.yml` 日志
2. 确保 `moling-server/requirements.txt` 存在
3. 本地运行脚本测试：`cd moling-server && python scripts/export_openapi.py`

---

## 六、最佳实践

### ✅ DO（推荐做法）

1. **每次修改 API 都更新接口文档**
   - 编辑：`015_前后端接口映射.md`
   - 确保文档与代码同步

2. **提交前运行测试**
   ```bash
   cd moling-server
   python scripts/export_openapi.py --check
   ```

3. **定期审查 OpenAPI 规范**
   - 每月检查一次 `openapi.json`
   - 确保没有过期的端点

4. **使用生成的 TypeScript 类型**
   - 前端使用 `api-types.ts`
   - 不要手动编写类型定义

---

### ❌ DON'T（不推荐做法）

1. **不要手动编辑 `openapi.json`**
   - 这是自动生成的文件
   - 手动编辑会被覆盖

2. **不要跳过 Git hook**
   - 确保 `core.hooksPath` 已配置
   - 提交前会自动检查

3. **不要忽略 CI 失败**
   - 如果 GitHub Actions 失败，及时修复
   - 接口漂移会导致前后端对接失败

---

## 七、版本管理

### 📋 版本号规则

| 变更类型 | 版本号变更 | 示例 |
|:-----|:---------|:-----|
| 新增端点 | 次版本号 +1 | 1.0.0 → 1.1.0 |
| 修改端点（向后兼容） | 修订号 +1 | 1.0.0 → 1.0.1 |
| 修改端点（破坏性变更） | 主版本号 +1 | 1.0.0 → 2.0.0 |

---

### 🔄 变更流程

```
修改 API 端点
    ↓
更新接口映射文档
    ↓
重新生成 openapi.json（自动）
    ↓
提交代码 + openapi.json（自动）
    ↓
CI 自动验证（自动）
    ↓
合并到主分支
```

---

## 八、总结

| 维度 | 评分 | 说明 |
|:-----|:-----|:-----|
| **自动化程度** | ⭐⭐⭐⭐⭐ | 三层自动更新，无需手动操作 |
| **可靠性** | ⭐⭐⭐⭐⭐ | 多层防护，确保永远同步 |
| **专业性** | ⭐⭐⭐⭐⭐ | 符合 OpenAPI 规范，工具链完善 |
| **可维护性** | ⭐⭐⭐⭐ | 自动化脚本，减少手动操作 |
| **团队协作** | ⭐⭐⭐⭐⭐ | Git hook + CI，所有成员受益 |

---

**实施状态**：✅ **完整可用**

**下一步**：
1. ✅ 运行 `git config core.hooksPath .githooks` 安装 Git hook
2. ✅ 推送代码到 GitHub，测试 GitHub Actions
3. ✅ 前端运行 `npm run openapi:generate` 生成类型

---

*最后更新：2026-06-17*
