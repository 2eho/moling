# 墨灵后端 API 修复方案

> 生成时间：2026-06-15
> 作者：CodeBuddy Code
> 目标：修复 `backend-api-review.md` 中发现的所有 API 问题

---

## 目录

1. [执行摘要](#一执行摘要)
2. [问题清单与修复方案](#二问题清单与修复方案)
   - [高优先级问题](#高优先级)
   - [中优先级问题](#中优先级)
   - [低优先级问题](#低优先级)
3. [影响分析](#三影响分析)
4. [测试计划](#四测试计划)
5. [回滚方案](#五回滚方案)
6. [实施时间表](#六实施时间表)

---

## 一、执行摘要

本文档针对 `backend-api-review.md` 中发现的 API 问题，提供详细的修复方案。

| 优先级 | 问题数量 | 预计工作量 |
|:-------|:---------|:-----------|
| 高 | 5 | 2-3 小时 |
| 中 | 2 | 3-4 小时 |
| 低 | 2 | 4-6 小时 |

**修复原则**：
1. 保持向后兼容（高优先级问题通过添加弃用警告而不是直接删除）
2. 先修复后端，再更新前端
3. 每一步都有对应的测试验证

---

## 二、问题清单与修复方案

### 高优先级

---

#### 问题 #1：路径不匹配 - Phase 4 建议端点

**问题描述**：
- 当前实现：`GET /api/v1/phase4/suggestions/{cid}`
- 应为：`GET /api/v1/phase4/chapters/{cid}/suggestions`
- 不符合 RESTful 规范

**影响范围**：
- 后端文件：`moling-server/app/router/phase4.py` 第 17 行
- 前端文件：`moling-web/src/lib/api.ts` 第（包含 `/phase4/suggestions/` 的行）

**修复步骤**：

1. **修改后端路由** (`moling-server/app/router/phase4.py`):

```python
# 修改前（第 17 行）
@router.get("/suggestions/{chapter_id}", response_model=Phase4SuggestionResp)

# 修改后
@router.get("/chapters/{chapter_id}/suggestions", response_model=Phase4SuggestionResp)
```

2. **添加旧路径兼容（临时）**：

```python
# 在 phase4.py 末尾添加（保持向后兼容）
@router.get("/suggestions/{chapter_id}", deprecated=True)
async def get_suggestions_legacy(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Phase4SuggestionResp:
    """获取章节的精修建议（弃用路径，请使用 /chapters/{cid}/suggestions）。"""
    import warnings
    warnings.warn("Use /phase4/chapters/{cid}/suggestions instead", DeprecationWarning)
    return await get_suggestions(chapter_id, db, current_user)
```

3. **更新前端代码** (`moling-web/src/lib/api.ts`):

```typescript
// 修改前
`getSuggestions: (chapterId: number) => apiClient.get(`/phase4/suggestions/${chapterId}`),

// 修改后
`getSuggestions: (chapterId: number) => apiClient.get(`/phase4/chapters/${chapterId}/suggestions`),
```

**验证方法**：
```bash
# 测试新路径
curl -X GET "http://localhost:8000/api/v1/phase4/chapters/1/suggestions"

# 测试旧路径（应返回弃用警告）
curl -X GET "http://localhost:8000/api/v1/phase4/suggestions/1"
```

---

#### 问题 #2：路径不匹配 - 秘密矩阵角色路径

**问题描述**：
- 当前实现：`GET /api/v1/projects/{pid}/secrets/{role}`
- 应为：`GET /api/v1/projects/{pid}/secrets/character/{name}`
- `{role}` 参数名容易混淆

**影响范围**：
- 后端文件：`moling-server/app/router/secret.py`（需要检查是否有旧路径）
- 前端文件：`moling-web/src/lib/api.ts`

**当前状态**：
✅ 经检查，`secret.py` 第 29 行已经正确实现为 `/character/{character_name}`。

**需要确认**：
1. 检查前端是否使用了正确的路径
2. 检查是否有其他地方使用了错误的路径 `{role}`

**修复步骤**：

1. **确认后端实现** - 无需修改（`secret.py` 已实现正确路径）

2. **更新前端代码** (如果使用了错误路径):

```typescript
// 确认路径正确（应该已经是）
`getCharacterSecrets: (projectId: number, characterName: string) =>
  apiClient.get(`/projects/${projectId}/secrets/character/${characterName}`),
```

**验证方法**：
```bash
# 测试正确路径
curl -X GET "http://localhost:8000/api/v1/projects/1/secrets/character/张三"
```

---

#### 问题 #3：重复端点 - 健康检查

**问题描述**：
- 当前有两个健康检查端点：
  - `GET /health` (无 `/api/v1` 前缀)
  - `GET /api/v1/health` (有 `/api/v1` 前缀)
- 建议统一为 `GET /api/v1/health`

**影响范围**：
- 后端文件：`moling-server/app/main.py` 第 245-262 行
- 后端文件：`moling-server/app/router/__init__.py` 第 51-53 行（通过 router 挂载）
- 前端文件：`moling-web/src/lib/api.ts`

**当前状态分析**：
1. `main.py` 第 245 行：定义了 `/health`
2. `main.py` 第 255 行：定义了 `/api/v1/health`
3. `router/__init__.py` 第 52 行：将 health_router 挂载到 `/health`（会成为 `/api/v1/health`）
4. `router/__init__.py` 第 57-61 行：定义了 `/system/health` 别名

**存在重复/冲突**：
- `main.py` 直接定义的 `/api/v1/health` 和通过 router 挂载的 `/api/v1/health` 可能冲突

**修复步骤**：

1. **移除 `main.py` 中的重复定义**：

```python
# moling-server/app/main.py

# 删除或注释掉第 245-252 行
# @app.get("/health", tags=["Health"])
# async def health_check():
#     """健康检查端点，返回服务状态。"""
#     return {
#         "status": "healthy",
#         "version": __version__,
#         "service": "moling-api",
#     }

# 删除或注释掉第 255-262 行（因为 router 中已经挂载了）
# @app.get("/api/v1/health", tags=["Health"])
# async def api_health_check():
#     """API 健康检查端点。"""
#     return {
#         "status": "healthy",
#         "version": __version__,
#         "service": "moling-api",
#     }
```

2. **确保 router 中的 health 路由正确**：

```python
# moling-server/app/router/health.py

# 确保返回格式一致
@router.get("", response_model=dict)
async def health_check(request: Request):
    """系统健康检查端点。"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": int(time.time()),
            "database": "connected",
            "code": 0,
            "message": "OK",
            "data": {"status": "healthy"},
            "request_id": None,
        }
    )
```

3. **更新前端代码** (如果使用 `/health` 路径):

```typescript
// moling-web/src/lib/api.ts

// 确保使用正确路径
checkSystemHealth: () => apiClient.get<ApiResponse<SystemHealthStatus>>("/system/health"),
```

**验证方法**：
```bash
# 测试正确路径
curl -X GET "http://localhost:8000/api/v1/health"

# 测试别名路径
curl -X GET "http://localhost:8000/api/v1/system/health"

# 确认旧路径已移除（应返回 404）
curl -X GET "http://localhost:8000/health"
```

---

#### 问题 #4：重复端点 - 卡牌列表

**问题描述**：
- 当前有两个获取卡牌池的端点：
  - `GET /api/v1/projects/{pid}/cards`
  - `GET /api/v1/projects/{pid}/cards/pool`
- 两者功能完全相同，都调用 `card_service.list_cards`
- 建议移除 `/cards`，保留 `/cards/pool`

**影响范围**：
- 后端文件：`moling-server/app/router/card.py` 第 18-25 行
- 前端文件：`moling-web/src/lib/api.ts` 第（包含 `/cards` 的行）
- 前端文件：`moling-web/src/lib/constants.ts` 第（包含 `CARDS` 的行）

**修复步骤**：

1. **标记旧端点为弃用** (`moling-server/app/router/card.py`):

```python
# 修改前（第 18-25 行）
@router.get("/cards", response_model=CardPoolListResp)
async def list_cards(...):
    """List all cards in a project's card pool."""
    return await card_service.list_cards(...)
```

```python
# 修改后 - 标记为弃用
@router.get("/cards", response_model=CardPoolListResp, deprecated=True, tags=["cards (deprecated)"])
async def list_cards(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CardPoolListResp:
    """List all cards in a project's card pool. DEPRECATED: Use /cards/pool instead."""
    import warnings
    warnings.warn("Use /projects/{project_id}/cards/pool instead", DeprecationWarning)
    return await card_service.list_cards(db, current_user["id"], project_id)
```

2. **更新前端代码** - 将所有 `/cards` 调用改为 `/cards/pool`：

```typescript
// moling-web/src/lib/api.ts

// 修改前
getCardPool: (projectId: number) =>
  apiClient.get<ApiResponse<CardPoolListResp>>(`/projects/${projectId}/cards`),

// 修改后
getCardPool: (projectId: number) =>
  apiClient.get<ApiResponse<CardPoolListResp>>(`/projects/${projectId}/cards/pool`),
```

```typescript
// moling-web/src/lib/constants.ts

// 修改前
CARDS: "/cards",

// 修改后
CARDS: "/cards/pool",
```

**验证方法**：
```bash
# 测试新路径
curl -X GET "http://localhost:8000/api/v1/projects/1/cards/pool"

# 测试旧路径（应返回弃用警告）
curl -X GET "http://localhost:8000/api/v1/projects/1/cards"
```

---

#### 问题 #5：废弃端点 - 抽卡历史

**问题描述**：
- 当前有两个获取抽卡历史的端点：
  - `GET /api/v1/projects/{pid}/cards/history`
  - `GET /api/v1/projects/{pid}/cards/draw-history`
- `/cards/history` 应标记为废弃，统一使用 `/cards/draw-history`

**影响范围**：
- 后端文件：`moling-server/app/router/card.py` 第 72-82 行
- 前端文件：`moling-web/src/lib/api.ts`

**修复步骤**：

1. **标记旧端点为弃用** (`moling-server/app/router/card.py`):

```python
# 修改前（第 72-82 行）
@router.get("/cards/history", response_model=list)
async def get_draw_history(...):
    """Get draw history for a project."""
    return await card_service.get_draw_history(...)
```

```python
# 修改后 - 标记为弃用
@router.get("/cards/history", response_model=list, deprecated=True, tags=["cards (deprecated)"])
async def get_draw_history(
    project_id: int,
    chapter_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list:
    """Get draw history for a project. DEPRECATED: Use /cards/draw-history instead."""
    import warnings
    warnings.warn("Use /projects/{project_id}/cards/draw-history instead", DeprecationWarning)
    return await card_service.get_draw_history(
        db, current_user["id"], project_id, chapter_id
    )
```

2. **更新前端代码**：

```typescript
// moling-web/src/lib/api.ts

// 修改前
getDrawHistory: (projectId: number, chapterId?: number) =>
  apiClient.get(`/projects/${projectId}/cards/history`, { params: { chapter_id: chapterId } }),

// 修改后
getDrawHistory: (projectId: number, chapterId?: number) =>
  apiClient.get(`/projects/${projectId}/cards/draw-history`, { params: { chapter_id: chapterId } }),
```

**验证方法**：
```bash
# 测试新路径
curl -X GET "http://localhost:8000/api/v1/projects/1/cards/draw-history"

# 测试旧路径（应返回弃用警告）
curl -X GET "http://localhost:8000/api/v1/projects/1/cards/history"
```

---

### 中优先级

---

#### 问题 #6：参数名不一致

**问题描述**：
- 检查所有端点的路径参数名、查询参数名是否与文档一致
- 特别关注 `nickname` vs `username`、`pid` vs `project_id` 等

**影响范围**：
- 所有路由文件
- OpenAPI 文档 (`openapi.yaml`)

**修复步骤**：

1. **创建参数命名规范文档**：

| 参数类型 | 推荐命名 | 示例 |
|:---------|:---------|:-----|
| 项目 ID | `project_id` | `/projects/{project_id}` |
| 章节 ID | `chapter_id` | `/chapters/{chapter_id}` |
| 卡牌 ID | `card_id` | `/cards/{card_id}` |
| 用户昵称 | `nickname` | `requestBody.nickname` |
| 分页页码 | `page` | `?page=1` |
| 分页大小 | `page_size` | `?page_size=20` |

2. **审计现有端点**：

使用以下命令搜索不一致的参数名：

```bash
# 搜索路径参数
grep -r "{pid}" moling-server/app/router/
grep -r "{cid}" moling-server/app/router/

# 搜索查询参数
grep -r "nickname" moling-server/app/router/
```

3. **逐个修复不一致的参数名**：

**示例修复** - 如果发现有使用 `{pid}` 的地方：

```python
# 修改前
@router.get("/projects/{pid}/chapters")

# 修改后
@router.get("/projects/{project_id}/chapters")
async def list_chapters(project_id: int, ...):
    ...
```

**注意**：修改路径参数名是**破坏性变更**，需要：
1. 先添加弃用警告
2. 更新前端代码
3. 在下个主版本中移除旧路径

---

#### 问题 #7：响应字段名不一致

**问题描述**：
- 检查所有响应的字段名是否与文档一致
- 特别关注 `created_at` vs `createdAt`、`updated_at` vs `updatedAt` 等

**影响范围**：
- 所有 Schema 定义文件 (`moling-server/app/schemas/`)
- 所有 Service 文件 (`moling-server/app/service/`)

**修复步骤**：

1. **确定命名规范**：
   - **选项 A**：使用 `snake_case` (`created_at`) - Python 惯例
   - **选项 B**：使用 `camelCase` (`createdAt`) - JSON/JavaScript 惯例
   - **建议**：保持 `snake_case`（后端 Python 风格），前端自行转换

2. **审计响应 Schema**：

```bash
# 搜索可能的字段名不一致
grep -r "created_at\|createdAt" moling-server/app/schemas/
grep -r "updated_at\|updatedAt" moling-server/app/schemas/
```

3. **统一字段命名**：

**示例修复** (`moling-server/app/schemas/chapter.py`):

```python
# 修改前
class ChapterResp(BaseModel):
    id: int
    title: str
    createdAt: datetime  # 不一致的命名
    updatedAt: datetime  # 不一致的命名

# 修改后
class ChapterResp(BaseModel):
    id: int
    title: str
    created_at: datetime  # 统一为 snake_case
    updated_at: datetime  # 统一为 snake_case
    
    class Config:
        # 可选：序列化时转换为 camelCase
        alias_generator = lambda string: ''.join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(string.split('_'))
        )
        allow_population_by_field_name = True
```

**或者**，如果希望 JSON 响应使用 `camelCase`：

```python
# 使用 Pydantic 的别名功能
from pydantic import Field

class ChapterResp(BaseModel):
    id: int
    title: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    
    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

---

### 低优先级

---

#### 问题 #8：添加单元测试

**问题描述**：
- 为所有端点添加测试用例
- 确保 API 行为符合预期

**修复步骤**：

1. **创建测试目录结构**：

```
moling-server/tests/
├── __init__.py
├── conftest.py           # 测试配置和 fixtures
├── test_auth.py          # 认证相关测试
├── test_project.py       # 项目管理测试
├── test_chapter.py       # 章节管理测试
├── test_card.py          # 卡牌管理测试
├── test_phase4.py       # Phase 4 测试
└── ...
```

2. **编写测试用例示例** (`tests/test_card.py`):

```python
"""测试卡牌管理 API。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.dependencies import get_db


@pytest.fixture
def client():
    """创建测试客户端。"""
    return TestClient(app)


@pytest.fixture
async def db_session():
    """创建测试数据库会话。"""
    async for session in get_db():
        yield session


def test_get_card_pool(client: TestClient):
    """测试获取卡牌池。"""
    response = client.get(
        "/api/v1/projects/1/cards/pool",
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert data["code"] == 0
    assert "data" in data


def test_get_card_pool_deprecated(client: TestClient):
    """测试废弃的 /cards 端点仍然可用。"""
    response = client.get(
        "/api/v1/projects/1/cards",
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    # 检查是否有弃用警告
    assert "deprecated" in response.headers.get("Warning", "").lower()


@pytest.mark.asyncio
async def test_draw_cards(db_session: AsyncSession):
    """测试抽卡功能。"""
    from app.service.card_service import card_service
    
    result = await card_service.draw_cards(
        db_session,
        user_id=1,
        project_id=1,
        req={"card_ids": [1, 2, 3], "weights": [1, 1, 1]}
    )
    assert "cards" in result
    assert len(result["cards"]) <= 3
```

3. **运行测试**：

```bash
cd moling-server
pytest tests/ -v
```

---

#### 问题 #9：添加集成测试

**问题描述**：
- 测试端点之间的联动
- 确保工作流程正确

**修复步骤**：

1. **创建集成测试文件** (`tests/test_integration.py`):

```python
"""集成测试 - 测试完整工作流程。"""

import pytest
from fastapi.testclient import TestClient


def test_chapter_workflow(client: TestClient):
    """测试章节完整工作流程：创建 → 生成 → 确认。"""
    
    # 1. 创建章节
    create_resp = client.post(
        "/api/v1/projects/1/chapters",
        json={"title": "测试章节", "content": ""},
        headers={"Authorization": "Bearer test-token"}
    )
    assert create_resp.status_code == 201
    chapter_id = create_resp.json()["data"]["id"]
    
    # 2. 生成章节内容
    generate_resp = client.post(
        f"/api/v1/projects/1/chapters/{chapter_id}/generate",
        json={"card_ids": [1, 2, 3]},
        headers={"Authorization": "Bearer test-token"}
    )
    assert generate_resp.status_code == 202
    task_id = generate_resp.json()["data"]["task_id"]
    
    # 3. 轮询任务状态
    import time
    for _ in range(10):
        status_resp = client.get(
            f"/api/v1/generate/{task_id}/status",
            headers={"Authorization": "Bearer test-token"}
        )
        assert status_resp.status_code == 200
        if status_resp.json()["data"]["status"] == "completed":
            break
        time.sleep(1)
    
    # 4. 确认收纳
    confirm_resp = client.post(
        f"/api/v1/projects/1/chapters/{chapter_id}/confirm",
        json={"nonce": "test-nonce"},
        headers={"Authorization": "Bearer test-token"}
    )
    assert confirm_resp.status_code == 202


def test_card_draw_workflow(client: TestClient):
    """测试抽卡完整工作流程：获取池 → 抽卡 → 查看历史。"""
    
    # 1. 获取卡牌池
    pool_resp = client.get(
        "/api/v1/projects/1/cards/pool",
        headers={"Authorization": "Bearer test-token"}
    )
    assert pool_resp.status_code == 200
    
    # 2. 执行抽卡
    draw_resp = client.post(
        "/api/v1/projects/1/cards/draw",
        json={"chapter_id": 1, "keep_card_ids": []},
        headers={"Authorization": "Bearer test-token"}
    )
    assert draw_resp.status_code == 200
    
    # 3. 查看抽卡历史
    history_resp = client.get(
        "/api/v1/projects/1/cards/draw-history",
        headers={"Authorization": "Bearer test-token"}
    )
    assert history_resp.status_code == 200
    assert len(history_resp.json()["data"]) > 0
```

2. **运行集成测试**：

```bash
cd moling-server
pytest tests/test_integration.py -v
```

---

## 三、影响分析

### 前端代码影响清单

| 后端变更 | 受影响的前端文件 | 影响程度 |
|:---------|:-----------------|:---------|
| Phase 4 路径修改 | `moling-web/src/lib/api.ts` | 高 - 需要立即更新 |
| 健康检查路径统一 | `moling-web/src/lib/api.ts`, `moling-web/src/lib/constants.ts` | 中 - 需要更新 |
| 卡牌端点弃用 | `moling-web/src/lib/api.ts`, `moling-web/src/lib/constants.ts` | 中 - 需要更新 |
| 抽卡历史端点弃用 | `moling-web/src/lib/api.ts` | 低 - 需要更新 |

### 前端更新步骤

1. **搜索所有受影响的 API 调用**：

```bash
cd moling-web
grep -r "/phase4/suggestions" src/
grep -r "/cards\"" src/  # 注意区分 /cards 和 /cards/pool
grep -r "/cards/history" src/
```

2. **批量更新前端代码**：

使用 IDE 的批量替换功能：
- 替换 `/phase4/suggestions/` → `/phase4/chapters/${chapterId}/suggestions`
- 替换 `/cards"` → `/cards/pool"` (需要小心处理)
- 替换 `/cards/history` → `/cards/draw-history`

3. **测试前端功能**：

```bash
cd moling-web
npm run dev
# 手动测试所有受影响的功能
```

---

## 四、测试计划

### 单元测试

**目标**：覆盖所有 API 端点

**工具**：
- `pytest` - Python 测试框架
- `httpx` - HTTP 客户端（用于测试 FastAPI）

**测试清单**：

| 模块 | 测试用例数 | 状态 |
|:-----|:----------|:-----|
| 认证 (Auth) | 7 | ❌ 待添加 |
| 项目 (Projects) | 6 | ❌ 待添加 |
| 章节 (Chapters) | 12 | ❌ 待添加 |
| 卡牌 (Cards) | 8 | ❌ 待添加 |
| 生成 (Generation) | 2 | ❌ 待添加 |
| 四库 (Vault) | 15 | ❌ 待添加 |
| Phase 4 | 7 | ❌ 待添加 |
| 健康 (Health) | 3 | ❌ 待添加 |

### 集成测试

**目标**：测试完整工作流程

**测试场景**：

1. **用户注册 → 登录 → 创建项目 → 创建章节 → 生成内容**
2. **卡牌抽取 → 查看历史 → 退役卡牌**
3. **四库管理 → 人物创建 → 秘密矩阵配置**
4. **Phase 4 质检 → 获取建议 → 应用建议**

### API 文档测试

**目标**：确保 OpenAPI 文档与实际实现一致

**工具**：
- `openapi-spec-validator` - 验证 OpenAPI 文档
- `schemathesis` - 基于 OpenAPI 文档的自动化测试

**测试方法**：

```bash
# 1. 导出 OpenAPI 文档
curl -X GET "http://localhost:8000/api/v1/openapi.json" > openapi-actual.json

# 2. 与文档对比
diff openapi-actual.json openapi.yaml

# 3. 验证 OpenAPI 文档格式
pip install openapi-spec-validator
openapi-spec-validator openapi.yaml
```

---

## 五、回滚方案

### 回滚触发条件

1. **单元测试失败率 > 10%**
2. **集成测试失败**
3. **前端功能异常**
4. **性能下降 > 20%**

### 回滚步骤

#### 方案 A：Git 回滚（推荐）

```bash
# 1. 查看提交历史
git log --oneline -10

# 2. 回滚到修复前的版本
git revert <commit-hash>

# 3. 推送回滚
git push origin main
```

#### 方案 B：功能开关回滚

**在代码中添加功能开关**：

```python
# moling-server/app/config.py

class Settings(BaseSettings):
    # ... 其他配置 ...
    
    # 功能开关
    ENABLE_NEW_PHASE4_PATH: bool = False
    ENABLE_DEPRECATED_WARNINGS: bool = True
```

```python
# moling-server/app/router/phase4.py

@router.get("/chapters/{chapter_id}/suggestions", response_model=Phase4SuggestionResp)
async def get_suggestions_new(...):
    """新路径实现。"""
    ...

@router.get("/suggestions/{chapter_id}", response_model=Phase4SuggestionResp)
async def get_suggestions_old(...):
    """旧路径实现（可通过配置禁用）。"""
    from app.config import get_settings
    settings = get_settings()
    
    if not settings.ENABLE_DEPRECATED_WARNINGS:
        raise HTTPException(status_code=410, detail="This endpoint is deprecated. Use /chapters/{cid}/suggestions instead.")
    
    # 调用新路径的实现
    return await get_suggestions_new(chapter_id, db, current_user)
```

### 回滚验证

```bash
# 1. 确认服务正常运行
curl -X GET "http://localhost:8000/api/v1/health"

# 2. 确认回滚的端点可用
curl -X GET "http://localhost:8000/api/v1/phase4/suggestions/1"

# 3. 运行测试套件
cd moling-server
pytest tests/ -v
```

---

## 六、实施时间表

### 阶段 1：高优先级问题修复（预计 1 天）

| 时间 | 任务 | 负责人 |
|:-----|:-----|:---------|
| 上午 | 修复 Phase 4 路径 | 后端开发 |
| 上午 | 修复健康检查端点 | 后端开发 |
| 下午 | 标记废弃端点 | 后端开发 |
| 下午 | 更新前端代码 | 前端开发 |
| 晚上 | 测试验证 | 测试/QA |

### 阶段 2：中优先级问题修复（预计 1-2 天）

| 时间 | 任务 | 负责人 |
|:-----|:-----|:---------|
| 第 1 天上午 | 参数名审计与修复 | 后端开发 |
| 第 1 天下午 | 响应字段名审计与修复 | 后端开发 |
| 第 2 天 | 更新 OpenAPI 文档 | 后端开发 |
| 第 2 天晚上 | 测试验证 | 测试/QA |

### 阶段 3：低优先级问题修复（预计 2-3 天）

| 时间 | 任务 | 负责人 |
|:-----|:-----|:---------|
| 第 1 天 | 添加单元测试（核心模块） | 后端开发 |
| 第 2 天 | 添加单元测试（其他模块） | 后端开发 |
| 第 3 天 | 添加集成测试 | 后端开发 |
| 第 3 天晚上 | 测试验证 | 测试/QA |

---

## 七、总结

本修复方案涵盖了 `backend-api-review.md` 中发现的所有问题，按照优先级分阶段实施。

**关键要点**：
1. ✅ 保持向后兼容 - 通过弃用警告而非直接删除
2. ✅ 先后端后前端 - 确保 API 稳定后再更新前端
3. ✅ 充分测试 - 每个修复都有对应的测试验证
4. ✅ 可回滚 - 提供详细的回滚方案

**后续工作**：
- 定期审查 API 与文档的一致性
- 建立 API 变更管理流程
- 添加 API 版本控制（如果需要）

---

*文档生成完毕*
