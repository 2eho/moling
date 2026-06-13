# 墨灵项目导入错误修复报告

## 修复时间
2026-06-14

## 问题描述
后端服务器因为导入错误无法启动。

## 修复的问题

### 1. 类名不匹配：`DrawRecord` vs `DrawHistory`

**问题文件：**
- `app/router/chapter.py` (第 19 行)
- `app/service/card_service.py` (第 21 行)

**问题描述：**
这两个文件尝试从 `app.models.draw_history` 导入 `DrawRecord`，但实际类名是 `DrawHistory`。

**修复方法：**
使用 `as` 别名保持向后兼容：
```python
from app.models.draw_history import DrawHistory as DrawRecord
```

**修复的文件：**
- `app/router/chapter.py`
- `app/service/card_service.py`

---

### 2. 缺少导入：`DrawCardResp`

**问题文件：**
- `app/router/chapter.py` (第 247 行)

**问题描述：**
`chapter.py` 在第 247 行使用了 `DrawCardResp` 作为 response_model，但没有导入这个类。

**修复方法：**
添加导入语句：
```python
from app.schemas.card import DrawCardResp
```

**修复的文件：**
- `app/router/chapter.py`

---

### 3. 路由重复注册导致路径冲突

**问题文件：**
- `app/router/__init__.py` (第 49-54 行)

**问题描述：**
`ingest_router` 被包含了两次：
1. 第一次：`prefix="/api/v1/ingest"` (第 49 行)
2. 第二次：`prefix="/api/v1/projects/{project_id}/import"` (第 50-54 行)

由于 `ingest_router` 中的路径已经包含了 `project_id` 参数（例如 `/projects/{project_id}/jobs`），第二次包含时会导致路径变成 `/api/v1/projects/{project_id}/import/projects/{project_id}/jobs`，其中 `project_id` 出现了两次，导致 FastAPI 报错：`ValueError: Duplicated param name project_id`

**修复方法：**
注释掉重复的路由注册（第 50-54 行），保留第一次的注册。

**修复的文件：**
- `app/router/__init__.py`

---

## 测试验证

修复后，执行以下命令验证导入是否成功：
```bash
cd "C:\Users\Admin\Desktop\新建文件夹 (2)\moling-server"
python -c "from app.main import app"
```

**结果：** ✅ 导入成功，没有错误输出。

---

## 修复的文件列表

1. `app/router/chapter.py`
   - 修改导入：`DrawRecord` → `DrawHistory as DrawRecord`
   - 添加导入：`from app.schemas.card import DrawCardResp`

2. `app/service/card_service.py`
   - 修改导入：`DrawRecord` → `DrawHistory as DrawRecord`

3. `app/router/__init__.py`
   - 注释掉重复的 `ingest_router` 注册

---

## 建议

1. **统一命名规范**：建议将 `app/models/draw_history.py` 中的类名统一为 `DrawRecord` 或 `DrawHistory`，避免混淆。
   - 如果改为 `DrawRecord`，需要修改 `draw_history.py` 中的类名定义
   - 如果保持 `DrawHistory`，建议在所有使用处统一使用 `DrawHistory`（不再使用别名）

2. **路由设计审查**：建议审查 `app/ingest/router.py` 的路由设计，确保它可以被正确地包含在多个路径下，或者拆分为多个独立的 router。

3. **单元测试**：建议添加导入测试的单元测试，在 CI/CD 过程中自动检测导入错误。

---

## 后续步骤

1. ✅ 导入错误已修复
2. ⏳ 启动后端服务器进行测试
3. ⏳ 运行完整的测试套件
4. ⏳ 审查其他潜在的导入问题

---

**修复工程师：** CodeBuddy Code
**修复日期：** 2026-06-14
