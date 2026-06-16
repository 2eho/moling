# OpenAPI 规范管理实施报告

生成时间：2026-06-17
执行人：CodeBuddy Code

## 一、已完成的任务

### ✅ 1. 创建 OpenAPI 导出脚本

**文件**：`moling-server/scripts/export_openapi.py`

**功能**：
- 导出 OpenAPI 规范到 JSON 或 YAML 格式
- 检查当前规范是否与快照一致（用于 CI）
- 使用方法：
  ```bash
  cd moling-server
  python scripts/export_openapi.py              # 导出到 ../../openapi.json
  python scripts/export_openapi.py --yaml        # 同时导出 YAML 格式
  python scripts/export_openapi.py --check       # 检查是否与快照一致
  ```

---

### ✅ 2. 修改 `main.py` 自动保存 OpenAPI 规范

**文件**：`moling-server/app/main.py`

**修改内容**：
- 在应用启动时自动保存 OpenAPI 规范到项目根目录
- 仅在非生产环境下生效（避免生产环境写入文件）
- 保存路径：`../../openapi.json`（项目根目录）

**代码位置**：第 324 行后（路由注册之后）

---

### ✅ 3. 添加前端 `package.json` 脚本

**文件**：`moling-web/package.json`

**新增脚本**：
```json
{
  "scripts": {
    "openapi:fetch": "curl -s http://localhost:8000/openapi.json -o ../openapi.json",
    "openapi:check": "node scripts/check-openapi.js",
    "openapi:generate": "npx openapi-typescript ../openapi.json -o src/lib/api-types.ts"
  }
}
```

**说明**：
- `openapi:fetch`：从运行中的后端获取 OpenAPI 规范
- `openapi:check`：检查 OpenAPI 规范是否一致（需要创建 `scripts/check-openapi.js`）
- `openapi:generate`：根据 OpenAPI 规范生成 TypeScript 类型定义（需要安装 `openapi-typescript`）

---

### ✅ 4. 添加 GitHub Actions CI 验证

**文件**：`.github/workflows/openapi-check.yml`

**功能**：
- 当 `moling-server/**` 或 `openapi.json` 变更时自动运行
- 检查代码中的 OpenAPI 规范是否与提交的 `openapi.json` 一致
- 如果不一致，CI 失败并提示运行导出脚本

**工作流程**：
1. 检出代码
2. 设置 Python 3.10
3. 安装依赖（需要 `requirements.txt` 或类似文件）
4. 运行 `python scripts/export_openapi.py --check`

---

## 二、待手动完成的任务

### ⚠️ 1. 生成 `openapi.json` 静态文件

**原因**：
- 后端当前未运行
- 导出脚本需要所有依赖已安装
- 环境存在 Python/pip 路径问题

**手动步骤**（当后端可运行时）：

```bash
# 方案 A：从运行中的后端获取（推荐）
# 1. 启动后端
cd moling-server
python -m uvicorn app.main:app --reload

# 2. 在另一个终端获取 OpenAPI 规范
curl http://localhost:8000/openapi.json -o ../openapi.json

# 方案 B：运行导出脚本
cd moling-server
python scripts/export_openapi.py
```

---

### ⚠️ 2. 验证 API 对齐改动已记录在 OpenAPI 规范中

**需要验证的改动**（来自 `API_ALIGNMENT_REPORT.md`）：

| 序号 | 改动内容 | 验证方法 |
|:-----|:---------|:---------|
| 1 | 删除 `weaveApi.getById` | 检查 `openapi.json` 中是否没有 `/weave/patterns/{patternId}` 端点 |
| 2 | 修改 `importApi.uploadAndImport` | 检查 `/projects/{projectId}/import/upload` 端点是否存在 |
| 3 | 删除 `draftApi` | 检查是否没有 `/projects/{projectId}/chapters/{chapterId}/draft` 端点 |
| 4 | 删除 `settingsApi.updateProjectSettings` | 检查是否没有 `/settings/project/{projectId}` 端点 |
| 5 | 添加 `redraw` 端点（占位符） | 检查是否有 `/projects/{pid}/chapters/{id}/redraw` 端点 |
| 6 | 修改 `ingest/router.py` 支持文件上传 | 检查 `/projects/{pid}/import` 端点是否支持 `UploadFile` |

**验证步骤**：
1. 生成 `openapi.json`
2. 搜索上述端点，确认与 `API_ALIGNMENT_REPORT.md` 一致
3. 如果不一致，修改后端代码并重新导出

---

## 三、使用指南

### 📋 日常开发流程

```
1. 后端开发者修改 API 端点
   ↓
2. 运行：cd moling-server && python scripts/export_openapi.py
   ↓
3. 自动更新 openapi.json（项目根目录）
   ↓
4. 提交代码 + openapi.json 到 Git
   ↓
5. CI 自动验证 openapi.json 是否与实现一致
   ↓
6. 前端开发者拉取代码，获得最新 openapi.json
```

### 🔧 前端使用流程

```bash
# 前端基于 openapi.json 生成 TypeScript 类型定义
cd moling-web
npm install openapi-typescript --save-dev
npm run openapi:generate

# 输出：src/lib/api-types.ts（自动生成的类型）
```

---

## 四、文件清单

| 文件 | 状态 | 说明 |
|:-----|:-----|:---------|
| `moling-server/scripts/export_openapi.py` | ✅ 已创建 | OpenAPI 导出脚本 |
| `moling-server/app/main.py` | ✅ 已修改 | 自动保存 OpenAPI 规范 |
| `moling-web/package.json` | ✅ 已修改 | 新增 openapi 脚本 |
| `.github/workflows/openapi-check.yml` | ✅ 已创建 | CI 验证工作流 |
| `openapi.json` | ⚠️ 待生成 | OpenAPI 规范（静态快照） |
| `OPENAPI_MANAGEMENT_REPORT.md` | ✅ 已创建 | 本文档 |

---

## 五、下一步建议

1. **启动后端**，运行导出脚本生成 `openapi.json`
2. **提交 `openapi.json` 到 Git**（作为静态快照）
3. **安装 `openapi-typescript`**，前端基于规范生成类型定义
4. **完善 CI 配置**（确保 `requirements.txt` 存在，包含所有依赖）
5. **验证 API 对齐改动**是否已正确记录在规范中

---

## 六、关键技术决策

| 决策 | 理由 |
|:-----|:-----|
| 静态快照 + 自动导出 | 前后端解耦，前端可独立开发 |
| 开发模式下自动保存 | 减少忘记导出的情况 |
| CI 验证 | 检测接口漂移，确保规范与实现一致 |
| 项目根目录存放 | 前后端共用，易于访问 |

---

**实施状态**：✅ 文件创建完成，⚠️ 需要手动生成 `openapi.json`
