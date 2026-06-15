# 墨灵后端 API 差异分析报告

> 生成时间：2026-06-15
> 分析范围：`moling-server/app` 目录
> 对比文档：`015_54298a88_前后端接口映射.md`

---

## 一、执行摘要

| 项目 | 数量 |
|:-----|-----:|
| 文档中定义的端点总数 | 88 |
| 后端实际实现的端点数 | 97 |
| 完全匹配 | 约 75 |
| 路径不匹配 | 3 |
| 方法不匹配 | 0 |
| 缺少的端点 | 5 |
| 文档中未记录的端点 | 约 12 |

---

## 二、路由挂载结构

### 2.1 前缀结构

根据 `main.py` 和 `router/__init__.py` 的分析：

```
/app
├── /health                           # 系统健康检查（无 /api/v1 前缀）
└── /api/v1                           # API 统一前缀
    ├── /auth/*                        # 认证相关
    ├── /projects/*                    # 项目管理
    ├── /projects/{pid}/health/*      # 项目健康检测
    ├── /projects/{pid}/chapters/*    # 章节管理
    ├── /projects/{pid}/cards/*       # 卡牌管理
    ├── /projects/{pid}/vault/*       # 四库管理
    ├── /projects/{pid}/secrets/*     # 秘密矩阵（在 project.py 中）
    ├── /generate/*                   # 生成任务
    ├── /health/*                     # 健康检查
    ├── /system/health                # 系统健康别名
    ├── /admin/*                      # 管理后台
    ├── /notifications/*              # 通知中心
    ├── /settings/*                   # 用户设置
    ├── /templates/*                  # 模板管理
    ├── /phase4/*                     # Phase 4 质检
    ├── /weave/*                      # 编织模式
    ├── /subscriptions/*              # 订阅管理
    └── /import/*                     # 导入功能（ingest）
```

---

## 三、详细端点对比

### 3.1 认证相关（Auth）

#### 后端实际路由（前缀：`/api/v1/auth`）

| 方法 | 路径 | 状态 |
|:-----|:-----|:-----|
| POST | `/api/v1/auth/register` | ✅ 匹配文档 8.2 |
| POST | `/api/v1/auth/login` | ✅ 匹配文档 8.1 |
| POST | `/api/v1/auth/refresh` | ✅ 匹配文档 8.3 |
| GET | `/api/v1/auth/me` | ✅ 匹配文档 8.4 |
| PUT | `/api/v1/auth/me` | ✅ 匹配文档 8.5 |
| POST | `/api/v1/auth/password-reset-request` | ✅ 匹配文档 8.6 |
| POST | `/api/v1/auth/password-reset` | ✅ 匹配文档 8.7 |

---

### 3.2 项目管理（Projects）

#### 后端实际路由（前缀：`/api/v1/projects`）

| 方法 | 路径 | 文档对应 | 状态 |
|:-----|:-----|:---------|:-----|
| GET | `/api/v1/projects` | 2.1 加载项目列表 | ✅ 匹配 |
| POST | `/api/v1/projects` | 2.4 创建项目 | ✅ 匹配 |
| GET | `/api/v1/projects/stats` | 2.2 项目统计概览 | ✅ 匹配 |
| GET | `/api/v1/projects/{project_id}` | 2.5 查看项目详情 | ✅ 匹配 |
| PUT | `/api/v1/projects/{project_id}` | 2.7 编辑项目 | ✅ 匹配 |
| DELETE | `/api/v1/projects/{project_id}` | 2.6 删除项目 | ✅ 匹配 |
| GET | `/api/v1/projects/{pid}/suggestions` | 3.4 创作建议 | ✅ 匹配 |
| GET | `/api/v1/projects/{pid}/secrets` | 5.6 秘密矩阵 | ✅ 匹配 |
| GET | `/api/v1/projects/{pid}/secrets/{role}` | 5.6.1 角色知识状态 | ⚠️ 路径异常：`{role}` 应为 `{name}` |
| PUT | `/api/v1/projects/{pid}/secrets/{secret_id}` | 5.6.2 编辑秘密 | ✅ 匹配 |
| GET | `/api/v1/projects/{pid}/cards/history` | - | ⚠️ 未记录端点 |
| GET | `/api/v1/projects/{pid}/health` | 4.3 健康告警 | ✅ 匹配 |
| POST | `/api/v1/projects/{pid}/health/refresh` | 2.13 刷新健康检查 | ✅ 匹配 |

**问题**：
1. `GET /projects/{pid}/secrets/{role}` - 路径参数名 `{role}` 容易混淆，建议改为 `{character_name}`

---

### 3.3 章节管理（Chapters）

#### 后端实际路由（前缀：`/api/v1/projects/{project_id}/chapters`）

| 方法 | 路径 | 文档对应 | 状态 |
|:-----|:-----|:---------|:-----|
| POST | `.../chapters` | 2.10 创建章节 | ✅ 匹配 |
| GET | `.../chapters` | 2.8 加载章节列表 | ✅ 匹配 |
| GET | `.../chapters/current` | 4.1 加载章节数据 | ✅ 匹配 |
| GET | `.../chapters/{chapter_id}` | 2.9 获取单章节详情 | ✅ 匹配 |
| PUT | `.../chapters/{chapter_id}` | 2.10 更新章节 | ✅ 匹配 |
| DELETE | `.../chapters/{chapter_id}` | 2.15 删除章节 | ✅ 匹配 |
| POST | `.../chapters/reorder` | 2.16 重排序章节 | ✅ 匹配 |
| POST | `.../chapters/{cid}/confirm` | 4.6 确认收纳 | ✅ 匹配 |
| POST | `.../chapters/{cid}/revise` | 4.7 拒稿 | ✅ 匹配 |
| GET | `.../chapters/{cid}/suggestions` | 4.8 加载AI建议 | ✅ 匹配 |
| POST | `.../chapters/{cid}/agent` | 4.9 工具栏AI指令 | ✅ 匹配 |
| POST | `.../chapters/{cid}/generate` | 4.5 生成章节 | ✅ 匹配 |

---

### 3.4 卡牌管理（Cards）

#### 后端实际路由（前缀：`/api/v1/projects/{project_id}/cards`）

| 方法 | 路径 | 文档对应 | 状态 |
|:-----|:-----|:---------|:-----|
| GET | `.../cards` | - | ⚠️ 重复端点（与 `/cards/pool` 功能相同） |
| POST | `.../cards/draw` | 4.4.2 执行抽卡 | ✅ 匹配 |
| POST | `.../cards` | 6.6 创建自定义卡牌 | ✅ 匹配 |
| POST | `.../cards/{card_id}/retire` | 6.7 退役卡牌 | ✅ 匹配 |
| GET | `.../cards/pool` | 6.5 卡牌池查看 | ✅ 匹配 |
| GET | `.../cards/history` | - | ❌ 废弃端点（应使用 `/cards/draw-history`） |
| GET | `.../cards/draw-history` | 6.8 抽卡历史 | ✅ 匹配 |
| GET | `.../cards/draw-history/{draw_id}` | 6.9 抽卡历史详情 | ✅ 匹配 |

**问题**：
1. `GET /cards` 和 `GET /cards/pool` 功能重复
2. `GET /cards/history` 应标记为废弃，统一使用 `/cards/draw-history`

---

### 3.5 生成任务（Generation）

#### 后端实际路由（前缀：`/api/v1/generate`）

| 方法 | 路径 | 文档对应 | 状态 |
|:-----|:-----|:---------|:-----|
| GET | `/api/v1/generate/{task_id}/status` | 4.5 生成章节（轮询） | ✅ 匹配 |
| POST | `/api/v1/generate/{task_id}/cancel` | 2.11 取消生成任务 | ✅ 匹配 |
| GET | `/api/v1/generate/history` | - | ⚠️ 未记录端点 |

---

### 3.6 四库管理（Vault）

#### 后端实际路由（前缀：`/api/v1/projects/{project_id}/vault`）

| 方法 | 路径 | 文档对应 | 状态 |
|:-----|:-----|:---------|:-----|
| GET | `.../vault/characters` | 5.2.1 加载人物列表 | ✅ 匹配 |
| GET | `.../vault/characters/{cid}` | 5.2.3 人物详情 | ✅ 匹配 |
| POST | `.../vault/characters` | 5.2.5 新增人物 | ✅ 匹配 |
| PUT | `.../vault/characters/{cid}` | 5.2.4 编辑人物 | ✅ 匹配 |
| DELETE | `.../vault/characters/{cid}` | - | ✅ 文档未明确但合理 |
| GET | `.../vault/timeline` | 5.3 时间线库 | ✅ 匹配 |
| GET | `.../vault/timeline/{eid}` | - | ⚠️ 未记录端点 |
| POST | `.../vault/timeline` | - | ⚠️ 未记录端点 |
| PUT | `.../vault/timeline/{eid}` | - | ⚠️ 未记录端点 |
| DELETE | `.../vault/timeline/{eid}` | - | ⚠️ 未记录端点 |
| GET | `.../vault/plot-promises` | 5.4 剧情承诺库 | ✅ 匹配 |
| GET | `.../vault/plot-promises/{pid}` | 5.4.0 承诺详情 | ✅ 匹配 |
| POST | `.../vault/plot-promises` | - | ⚠️ 未记录端点 |
| PUT | `.../vault/plot-promises/{pid}` | 5.4.1 编辑承诺 | ✅ 匹配 |
| DELETE | `.../vault/plot-promises/{pid}` | - | ⚠️ 未记录端点 |
| GET | `.../vault/world` | 5.5 世界观库 | ✅ 匹配 |
| GET | `.../vault/world/{eid}` | - | ⚠️ 未记录端点 |
| POST | `.../vault/world` | - | ⚠️ 未记录端点 |
| PUT | `.../vault/world/{eid}` | - | ⚠️ 未记录端点 |
| DELETE | `.../vault/world/{eid}` | - | ⚠️ 未记录端点 |
| GET | `.../vault/summary` | 5.1 加载四库总览 | ✅ 匹配 |
| POST | `.../vault/full-reanalyze` | 5.7 全量重新分析 | ✅ 匹配 |

---

### 3.7 健康检查（Health）

#### 后端实际路由

| 方法 | 路径 | 文档对应 | 状态 |
|:-----|:-----|:---------|:-----|
| GET | `/health` | - | ⚠️ 无 `/api/v1` 前缀 |
| GET | `/api/v1/health` | - | ⚠️ 重复端点（别名） |
| GET | `/api/v1/system/health` | 2.14 系统健康检查（别名） | ✅ 匹配 |

**问题**：
1. `/health` 和 `/api/v1/health` 都存在，建议统一为 `/api/v1/health`

---

### 3.8 管理后台（Admin）

#### 后端实际路由（前缀：`/api/v1/admin`）

| 方法 | 路径 | 文档对应 | 状态 |
|:-----|:-----|:---------|:-----|
| GET | `/api/v1/admin/llm-config` | 8.10.1 LLM配置获取 | ✅ 匹配 |
| POST | `/api/v1/admin/llm-config` | 8.10.2 LLM配置更新 | ✅ 匹配 |
| POST | `/api/v1/admin/llm-config/test` | 8.10.3 LLM配置测试 | ✅ 匹配 |
| GET | `/api/v1/admin/stats` | 8.10 管理后台概览 | ✅ 匹配 |
| GET | `/api/v1/admin/users` | 8.10 用户管理 | ✅ 匹配 |
| GET | `/api/v1/admin/projects` | 8.10.4 管理后台项目列表 | ✅ 匹配 |

---

### 3.9 通知中心（Notifications）

#### 后端实际路由（前缀：`/api/v1/notifications`）

| 方法 | 路径 | 文档对应 | 状态 |
|:-----|:-----|:---------|:-----|
| GET | `/api/v1/notifications` | 8.9 通知中心 | ✅ 匹配 |
| GET | `/api/v1/notifications/unread-count` | 8.9.1 未读通知计数 | ✅ 匹配 |
| POST | `/api/v1/notifications/{id}/read` | 8.9 标记已读 | ✅ 匹配 |
| POST | `/api/v1/notifications/read-all` | 8.9 全部已读 | ✅ 匹配 |
| DELETE | `/api/v1/notifications/{id}` | 8.9.2 删除通知 | ✅ 匹配 |

---

### 3.10 用户设置（Settings）

#### 后端实际路由（前缀：`/api/v1/settings`）

| 方法 | 路径 | 文档对应 | 状态 |
|:-----|:-----|:---------|:-----|
| GET | `/api/v1/settings` | 6.1 加载设置 | ✅ 匹配 |
| PUT | `/api/v1/settings` | 6.2 保存设置 | ✅ 匹配 |
| POST | `/api/v1/settings/change-password` | 6.12 修改密码 | ✅ 匹配 |
| GET | `/api/v1/settings/profile` | 6.13 获取个人资料 | ✅ 匹配 |
| PUT | `/api/v1/settings/profile` | 6.14 更新个人资料 | ✅ 匹配 |
| PATCH | `/api/v1/settings/health-monitor` | 6.3 健康监控 | ✅ 匹配 |
| POST | `/api/v1/settings/export` | 6.10 导出数据 | ✅ 匹配 |
| POST | `/api/v1/settings/clear-cache` | 6.11 清除缓存 | ✅ 匹配 |
| GET | `/api/v1/settings/phase4-review` | 6.4 Phase 4 质检模式 | ✅ 匹配 |
| PATCH | `/api/v1/settings/phase4-review` | 6.4 Phase 4 质检模式 | ✅ 匹配 |

---

### 3.11 模板管理（Templates）

#### 后端实际路由（前缀：`/api/v1/templates`）

| 方法 | 路径 | 文档对应 | 状态 |
|:-----|:-----|:---------|:-----|
| GET | `/api/v1/templates` | 3.3 模板列表 | ✅ 匹配 |
| GET | `/api/v1/templates/{id}` | 3.5 模板详情 | ✅ 匹配 |
| POST | `/api/v1/templates` | 3.6 创建模板 | ✅ 匹配 |
| PUT | `/api/v1/templates/{id}` | 3.7 更新模板 | ✅ 匹配 |
| DELETE | `/api/v1/templates/{id}` | 3.8 删除模板 | ✅ 匹配 |
| POST | `/api/v1/templates/{id}/create-project` | 3.9 从模板创建项目 | ✅ 匹配 |

---

### 3.12 Phase 4 质检（Phase4）

#### 后端实际路由（前缀：`/api/v1/phase4`）

| 方法 | 路径 | 文档对应 | 状态 |
|:-----|:-----|:---------|:-----|
| GET | `/api/v1/phase4/suggestions/{cid}` | - | ⚠️ 路径异常：应为 `/phase4/chapters/{cid}/suggestions` |
| POST | `/api/v1/phase4/apply` | 4.11 Phase 4 应用精修建议 | ✅ 匹配 |
| GET | `/api/v1/phase4/tasks/{tid}` | - | ⚠️ 未记录端点 |
| GET | `/api/v1/phase4/chapters/{cid}/tasks` | 4.12 章节Phase 4任务列表 | ✅ 匹配 |
| GET | `/api/v1/phase4/projects/{pid}/tasks` | 4.13 项目Phase 4任务列表 | ✅ 匹配 |
| GET | `/api/v1/phase4/pending-reviews` | 4.10 加载待审核数量 | ✅ 匹配 |
| POST | `/api/v1/phase4/reviews/{id}/approve` | - | ⚠️ 未记录端点 |
| POST | `/api/v1/phase4/reviews/{id}/reject` | - | ⚠️ 未记录端点 |

**问题**：
1. `GET /phase4/suggestions/{cid}` 路径不符合 RESTful 规范，建议改为 `/phase4/chapters/{cid}/suggestions`

---

### 3.13 编织模式（Weave）

#### 后端实际路由（前缀：`/api/v1/weave`）

| 方法 | 路径 | 文档对应 | 状态 |
|:-----|:-----|:---------|:-----|
| GET | `/api/v1/weave/patterns` | 2.12 编织模式列表 | ✅ 匹配 |
| GET | `/api/v1/weave/suggestions/{pid}` | - | ⚠️ 未记录端点 |
| POST | `/api/v1/weave/apply` | - | ⚠️ 未记录端点 |
| GET | `/api/v1/weave/analyze/{pid}` | - | ⚠️ 未记录端点 |

---

### 3.14 订阅管理（Subscriptions）

#### 后端实际路由（前缀：`/api/v1/subscriptions`）

| 方法 | 路径 | 文档对应 | 状态 |
|:-----|:-----|:---------|:-----|
| GET | `/api/v1/subscriptions/plans` | 8.8 定价页面 | ✅ 匹配 |
| POST | `/api/v1/subscriptions/create-checkout` | 8.8 定价页面 | ✅ 匹配 |
| POST | `/api/v1/subscriptions` | - | ⚠️ 未记录端点（可能是创建订阅） |
| GET | `/api/v1/subscriptions/current` | 8.8.1 当前订阅信息 | ✅ 匹配 |

---

### 3.15 导入功能（Import）

#### 后端实际路由（无统一前缀，直接挂载到 `/api/v1`）

| 方法 | 路径 | 文档对应 | 状态 |
|:-----|:-----|:---------|:-----|
| POST | `/api/v1/import` | 7.1 提交导入任务 | ✅ 匹配 |
| GET | `/api/v1/import/{job_id}` | 7.2 轮询导入进度 | ✅ 匹配 |
| GET | `/api/v1/import` | - | ⚠️ 未记录端点（可能是列表） |
| POST | `/api/v1/import/{job_id}/phase1` | 7.3 执行Phase 1 | ✅ 匹配 |
| GET | `/api/v1/import/{job_id}/phase1/result` | - | ⚠️ 未记录端点 |
| POST | `/api/v1/import/{job_id}/phase2` | 7.4 执行Phase 2 | ✅ 匹配 |
| GET | `/api/v1/import/{job_id}/phase2/result` | - | ⚠️ 未记录端点 |
| POST | `/api/v1/import/{job_id}/confirm` | 7.5 确认导入 | ✅ 匹配 |
| GET | `/api/v1/import/{job_id}/phase3/result` | - | ⚠️ 未记录端点 |
| POST | `/api/v1/import/full-import` | - | ⚠️ 未记录端点 |

---

## 四、主要问题汇总

### 4.1 路径不匹配

| 问题 | 后端实现 | 文档定义 | 建议 |
|:-----|:---------|:---------|:-----|
| 秘密矩阵角色路径 | `/secrets/{role}` | `/secrets/character/{name}` | 统一为 `/secrets/character/{name}` |
| Phase 4 建议路径 | `/phase4/suggestions/{cid}` | `/phase4/chapters/{cid}/suggestions` | 改为 RESTful 风格 |

### 4.2 重复端点

| 端点 | 说明 |
|:-----|:-----|
| `GET /health` 和 `GET /api/v1/health` | 建议统一为 `/api/v1/health` |
| `GET /cards` 和 `GET /cards/pool` | 功能重复，建议移除 `/cards` |

### 4.3 废弃端点

| 端点 | 说明 |
|:-----|:-----|
| `GET /cards/history` | 应使用 `/cards/draw-history` |

### 4.4 文档中未记录的端点

| 端点 | 说明 |
|:-----|:-----|
| `GET /generate/history` | 生成历史记录 |
| `GET /vault/timeline/{eid}` | 时间线详情 |
| `POST /vault/timeline` | 新增时间线事件 |
| `PUT /vault/timeline/{eid}` | 编辑时间线事件 |
| `DELETE /vault/timeline/{eid}` | 删除时间线事件 |
| `POST /vault/plot-promises` | 新增剧情承诺 |
| `DELETE /vault/plot-promises/{pid}` | 删除剧情承诺 |
| `GET /vault/world/{eid}` | 世界观详情 |
| `POST /vault/world` | 新增世界观条目 |
| `PUT /vault/world/{eid}` | 编辑世界观条目 |
| `DELETE /vault/world/{eid}` | 删除世界观条目 |
| `GET /weave/suggestions/{pid}` | 编织建议 |
| `POST /weave/apply` | 应用编织 |
| `GET /weave/analyze/{pid}` | 编织分析 |
| `POST /subscriptions` | 创建订阅 |
| `GET /import` | 导入列表 |

---

## 五、建议行动

### 5.1 高优先级

1. **统一健康检查路径**：移除 `/health`，只保留 `/api/v1/health` 和 `/api/v1/system/health`
2. **修复秘密矩阵路径**：将 `/secrets/{role}` 改为 `/secrets/character/{name}`
3. **修复 Phase 4 路径**：将 `/phase4/suggestions/{cid}` 改为 `/phase4/chapters/{cid}/suggestions`
4. **移除重复端点**：移除 `GET /cards`，保留 `GET /cards/pool`

### 5.2 中优先级

1. **更新文档**：将未记录的端点添加到接口文档中
2. **标记废弃端点**：在代码中标记 `GET /cards/history` 为废弃

### 5.3 低优先级

1. **添加单元测试**：为所有端点添加测试用例
2. **添加集成测试**：测试端点之间的联动

---

## 六、结论

后端 API 实现与文档定义基本匹配，主要差异在于：
1. 部分路径设计不符合 RESTful 规范
2. 存在少量重复和废弃端点
3. 部分 CRUD 端点未在文档中记录

建议按照优先级逐步修复上述问题，保持代码与文档的一致性。

---

*报告生成完毕*
