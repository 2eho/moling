# 墨灵项目 API 响应格式修复报告

**修复时间**: 2026-06-13  
**修复工程师**: API 修复工程师  
**审计轮次**: 第三轮

---

## 修复概览

本次修复针对第三轮审计发现的 4 个 API 响应格式问题，已全部修复完成。

| 问题编号 | 问题描述 | 状态 | 修复文件 |
|---------|---------|------|---------|
| 问题 1 | DELETE 端点返回 200 而非 204 | ✅ 已修复 | 3 个文件 |
| 问题 2 | health/alerts 响应缺少 checked_at 字段 | ✅ 已修复 | 1 个文件 |
| 问题 3 | export 端点应触发文件下载 | ✅ 已修复 | 1 个文件 |
| 问题 4 | redraw 端点响应格式不匹配 | ✅ 无需修改 | - |

---

## 详细修复记录

### 问题 1: DELETE 端点返回 204 而非 200

**问题描述**: 所有 DELETE 端点返回 200 状态码和 JSON 响应体，不符合 REST 规范（应返回 204 No Content）。

**修复方案**: 将所有 DELETE 端点的响应从 `SuccessResp(code=200, message="已删除")` 改为 `Response(status_code=204)`。

**修复文件**:

#### 1. `app/router/project.py`
- **方法**: `delete_project()` (第 123-131 行)
- **修改内容**:
  - 添加 `Response` 到导入语句：`from fastapi import APIRouter, Depends, Query, Response`
  - 移除 `response_model=SuccessResp` 装饰器参数
  - 修改返回类型：`-> SuccessResp:` 改为 `-> Response:`
  - 修改返回值：`return SuccessResp(code=200, message="项目已删除")` 改为 `return Response(status_code=204)`

#### 2. `app/router/chapter.py`
- **方法**: `delete_chapter()` (第 124-134 行)
- **修改内容**:
  - 添加 `Response` 到导入语句：`from fastapi import APIRouter, Depends, Query, Response`
  - 移除 `response_model=SuccessResp` 装饰器参数
  - 修改返回类型：`-> SuccessResp:` 改为 `-> Response:`
  - 修改返回值：`return SuccessResp(code=200, message="章节已删除")` 改为 `return Response(status_code=204)`

#### 3. `app/router/vault.py`
- **方法 1**: `delete_character()` (第 85-97 行)
- **方法 2**: `delete_timeline_event()` (第 159-171 行)
- **方法 3**: `delete_plot_promise()` (第 233-245 行)
- **方法 4**: `delete_world_entry()` (第 318-330 行)
- **修改内容**:
  - 添加 `Response` 到导入语句：`from fastapi import APIRouter, Depends, Response`
  - 所有 4 个方法都移除了 `response_model=SuccessResp` 装饰器参数
  - 所有 4 个方法都修改了返回类型：`-> SuccessResp:` 改为 `-> Response:`
  - 所有 4 个方法都修改了返回值：`return SuccessResp(code=200, message="已删除")` 改为 `return Response(status_code=204)`

---

### 问题 2: health/alerts 响应缺少 checked_at 字段

**问题描述**: `GET /projects/{project_id}/health/alerts` 端点返回的响应中缺少 `checked_at` 字段，不符合 API 文档定义。

**修复方案**: 在响应中添加 `checked_at` 字段，使用 UTC 时间戳。

**修复文件**:

#### `app/router/project.py`
- **方法**: `get_project_health_alerts()` (第 160-190 行)
- **修改内容**:
  - 修改返回值，添加 `checked_at` 字段：
  ```python
  return {
      "alerts": [HealthAlertResp.model_validate(a) for a in alerts],
      "checked_at": datetime.now(timezone.utc).isoformat(),
  }
  ```
  - 注意：文件已导入 `from datetime import datetime, timezone` (第 9 行)

---

### 问题 3: export 端点应触发文件下载

**问题描述**: `POST /settings/export` 端点直接返回 JSON 字典，应该返回文件下载响应。

**修复方案**: 改为返回 `FileResponse`，触发浏览器文件下载。

**修复文件**:

#### `app/router/setting.py`
- **方法**: `export_data()` (第 133-148 行)
- **修改内容**:
  - 添加必要的导入：
    ```python
    import json
    import tempfile
    from fastapi.responses import FileResponse
    ```
  - 修改方法签名：移除 `-> dict:` 返回类型注解
  - 修改方法实现：
    ```python
    @router.post("/export")
    async def export_data(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        """Export user data as JSON file download."""
        from app.dao import user_dao

        user = await user_dao.get(db, int(current_user["id"]))
        if user is None:
            raise NotFoundError(ErrorCode.USER_NOT_FOUND, "用户不存在")
        
        # 创建临时 JSON 文件
        data = {
            "email": user.email,
            "username": user.username,
            "settings": user.settings or {},
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            temp_path = f.name
        
        return FileResponse(
            path=temp_path,
            filename=f"moling-export-{user.id}.json",
            media_type="application/json"
        )
    ```

---

### 问题 4: redraw 端点响应格式不匹配

**问题描述**: `POST /projects/{project_id}/chapters/{chapter_id}/redraw` 端点返回 `DrawCardResp`，需确认是否与文档定义匹配。

**检查结果**:
- **当前实现**: 返回 `DrawCardResp`
- **DrawCardResp 定义** (`app/schemas/card.py` 第 41-47 行):
  ```python
  class DrawCardResp(BaseModel):
      cards: list[CardResp]  # 卡片列表
      draw_round: int  # 抽卡轮次
      remaining_redraws: int  # 剩余重抽次数
      recommended: list[CardResp]  # 推荐保留的卡片
  ```
- **文档要求**: `{cards: [...], remaining_redraws: N}`
- **结论**: `DrawCardResp` 包含 `cards` 和 `remaining_redraws` 字段，符合文档要求。额外字段 (`draw_round`, `recommended`) 不影响功能，符合 OpenAPI 规范。

**修复方案**: **无需修改**

---

## 测试建议

### 1. DELETE 端点测试
```bash
# 测试项目删除
curl -X DELETE http://localhost:8000/api/v1/projects/1 \
  -H "Authorization: Bearer <token>" \
  -v  # 查看响应头，应为 204 No Content

# 测试章节删除
curl -X DELETE http://localhost:8000/api/v1/projects/1/chapters/1 \
  -H "Authorization: Bearer <token>" \
  -v

# 测试角色删除
curl -X DELETE http://localhost:8000/api/v1/projects/1/vault/characters/1 \
  -H "Authorization: Bearer <token>" \
  -v
```

### 2. health/alerts 端点测试
```bash
curl http://localhost:8000/api/v1/projects/1/health/alerts \
  -H "Authorization: Bearer <token>"

# 预期响应：
# {
#   "alerts": [...],
#   "checked_at": "2026-06-13T10:30:00.123456+00:00"
# }
```

### 3. export 端点测试
```bash
curl -X POST http://localhost:8000/api/v1/settings/export \
  -H "Authorization: Bearer <token>" \
  -v

# 预期行为：
# 1. 响应头包含 Content-Disposition: attachment; filename="moling-export-1.json"
# 2. 浏览器自动触发文件下载
# 3. 下载的文件包含正确的 JSON 内容
```

---

## 影响范围

### 后端文件修改
- `app/router/project.py` - 2 个方法修改
- `app/router/chapter.py` - 1 个方法修改
- `app/router/vault.py` - 4 个方法修改
- `app/router/setting.py` - 1 个方法修改

### API 端点影响
- `DELETE /api/v1/projects/{project_id}` - 响应格式变更
- `DELETE /api/v1/projects/{project_id}/chapters/{chapter_id}` - 响应格式变更
- `DELETE /api/v1/projects/{project_id}/vault/characters/{character_id}` - 响应格式变更
- `DELETE /api/v1/projects/{project_id}/vault/timeline/{event_id}` - 响应格式变更
- `DELETE /api/v1/projects/{project_id}/vault/plot-promises/{promise_id}` - 响应格式变更
- `DELETE /api/v1/projects/{project_id}/vault/world/{entry_id}` - 响应格式变更
- `GET /api/v1/projects/{project_id}/health/alerts` - 响应添加字段
- `POST /api/v1/settings/export` - 响应格式变更（触发文件下载）

### 前端适配建议
1. **DELETE 端点**: 前端需要适配 204 No Content 响应（无响应体）
2. **health/alerts**: 前端需要读取新增的 `checked_at` 字段
3. **export**: 前端需要处理文件下载响应（可使用 `window.open()` 或 `<a>` 标签）

---

## 总结

✅ **所有 4 个问题已全部处理完成**
- 3 个文件修复（问题 1、2、3）
- 1 个无需修改（问题 4）
- 共修改 8 个 API 端点
- 所有修改符合 REST 规范和 API 文档定义

**下一步建议**:
1. 运行单元测试验证修改
2. 更新前端 API 调用代码
3. 更新 API 文档
4. 提交代码并进行集成测试
