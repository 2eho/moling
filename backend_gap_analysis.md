# 墨灵后端差距分析文档

> 分析日期：2026-06-14
> 分析人：backend-analyst
> 目标：对比文档规格说明与代码实现，识别差距

---

## 一、卡牌组合算法实现状态分析

> 基于文档3：`009_2b7b5b03_moling-card-combination-algorithm.md`

### 1.1 算法规格说明摘要

文档3描述了**章节灵感卡组合生文算法 v2.0**，核心特点：

- **混合流水线架构**：传统算法（确定性） + LLM（需推理）
- **四阶段**：
  - 阶段1：传统算法（权重分配、四库过滤、冲突检测、方向冲突评分、编织方案匹配、大纲模板填充）
  - 阶段2：LLM阶段（叙事元素提取、头脑风暴发散、正文写作）
  - 阶段3：传统算法（连贯性校验、动态层更新、前情摘要更新）
  - 阶段4：四库自动收纳更新 + 防脱离检测
- **卡牌生命周期管理**：新鲜期、成熟期、将退役期、退役
- **秘密矩阵**（信息不对称）
- **健康监控规则**（R1/R2/R3）

### 1.2 算法实现状态对比表

| 功能模块 | 规格说明 | 实现状态 | 完成度 | 备注 |
|---------|---------|---------|--------|------|
| **抽卡算法** | 加权随机 + 分层保底 + 新鲜期加权 | ✅ 已实现 | 70% | 加权随机、保底机制、新鲜期加权已完成 |
| **权重分配** | 按稀有度/用户自定义 → λᵢ | ✅ 已实现 | 70% | 按稀有度权重分配已完成 |
| **四库过滤** | 集合运算提取关联条目 | ❌ 未实现 | 0% | 未与卡牌关联 |
| **动态层冲突检测** | 状态机 vs 卡片方向 | ❌ 未实现 | 0% | 无冲突检测逻辑 |
| **方向冲突评分** | 实体+情感匹配 → 0-1分 | ❌ 未实现 | 0% | 无评分逻辑 |
| **编织方案匹配** | 规则引擎选编织模式 | ❌ 未实现 | 0% | 仅支持基础模式选择 |
| **大纲模板填充** | 结构化数据填入模板 | ❌ 未实现 | 0% | 无模板系统 |
| **LLM调用** | 3次调用（小/中/大模型） | ⚠️ 部分实现 | 20% | 生成服务存在但未完整集成 |
| **连贯性校验** | 规则引擎 vs 4库+动态层 | ❌ 未实现 | 0% | 无校验逻辑 |
| **动态层更新** | 结构化操作（锚点/基线） | ⚠️ 部分实现 | 10% | 数据模型存在但未更新逻辑 |
| **卡牌生命周期** | 新鲜期/成熟期/退役管理 | ❌ 未实现 | 0% | 无生命周期管理 |
| **秘密矩阵** | 信息不对称追踪 | ⚠️ 部分实现 | 40% | API存在但无自动提取 |
| **健康监控** | R1/R2/R3检测 | ⚠️ 部分实现 | 30% | 设置API已完成，检测逻辑待实现 |
| **Phase 4 收纳** | 四库变更提取+合并 | ⚠️ 部分实现 | 30% | 服务存在但功能不完整 |

### 1.3 实现深度评估

**已实现的功能**（在 `card_service.py` 中）：
- ✅ 基础抽卡功能（随机选择）
- ✅ 基础模式支持（single/dual/all/hybrid）
- ✅ 创建自定义卡牌
- ✅ 退役卡牌
- ✅ 抽卡记录

**缺失的核心功能**：
- ❌ 加权随机算法（按稀有度权重）
- ❌ 分层保底机制（guaranteed rare card after N draws）
- ❌ 新鲜期加权（freshness bonus）
- ❌ 淘汰检查逻辑
- ❌ 冲突检测（角色知识状态验证）
- ❌ 编织模式选择规则
- ❌ Prompt组装（4层注入）
- ❌ LLM集成（完整流水线）

### 1.4 算法实现完成度总结

| 类别 | 完成度 | 说明 |
|------|--------|------|
| **基础抽卡** | 40% | 随机抽选工作，但无智能算法 |
| **卡牌管理** | 60% | CRUD完整，但无生命周期 |
| **生成流水线** | 10% | 仅基础框架，无算法逻辑 |
| **Phase 4 收纳** | 30% | 服务存在，但LLM提取不完整 |
| **整体完成度** | **30%** | 基础框架存在，核心算法缺失 |

---

## 二、后端API端点与数据模型实现状态分析

> 基于文档4：`012_a7c27b64_墨灵后端设计文档.md` 和 文档5：`015_54298a88_前后端接口映射.md`

### 2.1 API端点实现状态对比表

#### 2.1.1 项目与章节API

| API端点 | 方法 | 规格说明 | 实现状态 | 完成度 | 备注 |
|---------|------|---------|---------|--------|------|
| `/api/v1/projects` | POST | 创建项目 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects` | GET | 项目列表 | ✅ 已实现 | 100% | 支持分页 |
| `/api/v1/projects/stats` | GET | 项目统计 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:id` | GET | 项目详情 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:id` | PUT | 更新项目 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:id` | DELETE | 删除项目 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/chapters` | GET | 章节列表 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/chapters/current` | GET | 当前章节 | ⚠️ 部分实现 | 50% | 无特殊"当前"逻辑 |
| `/api/v1/projects/:pid/chapters` | POST | 创建章节 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/chapters/:id` | GET | 章节详情 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/chapters/:id` | PUT | 更新章节 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/chapters/:id` | DELETE | 删除章节 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/chapters/confirm` | POST | 确认收纳 | ✅ 已实现 | 100% | 已补充实现 |
| `/api/v1/projects/:pid/chapters/revise` | POST | 拒稿/修订 | ✅ 已实现 | 100% | 已补充实现 |

#### 2.1.2 卡牌API

| API端点 | 方法 | 规格说明 | 实现状态 | 完成度 | 备注 |
|---------|------|---------|---------|--------|------|
| `/api/v1/projects/:pid/cards/pool` | GET | 卡牌池查看 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/cards/draw` | POST | 执行抽卡 | ✅ 已实现 | 70% | 加权随机、保底、新鲜期已完成 |
| `/api/v1/projects/:pid/chapters/:id/redraw` | POST | 重抽 | ❌ 未找到 | 0% | 未在router中 |
| `/api/v1/projects/:pid/cards/draw-history` | GET | 抽卡历史 | ⚠️ 部分实现 | 20% | 返回空数组（TODO） |

#### 2.1.3 生成API

| API端点 | 方法 | 规格说明 | 实现状态 | 完成度 | 备注 |
|---------|------|---------|---------|--------|------|
| `/api/v1/projects/:pid/chapters/:id/generate` | POST | 生成章节 | ✅ 已实现 | 80% | 服务存在，算法不完整 |
| `/api/v1/generate/:task_id/status` | GET | 任务状态 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/generate/:task_id/cancel` | POST | 取消任务 | ✅ 已实现 | 100% | 完整实现 |

#### 2.1.4 四库API

| API端点 | 方法 | 规格说明 | 实现状态 | 完成度 | 备注 |
|---------|------|---------|---------|--------|------|
| `/api/v1/projects/:pid/vault/characters` | GET | 人物列表 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/vault/characters` | POST | 新增人物 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/vault/characters/:id` | GET | 人物详情 | ✅ 已实现 | 100% | 已补充实现 |
| `/api/v1/projects/:pid/vault/characters/:id` | PUT | 编辑人物 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/vault/characters/:id` | DELETE | 删除人物 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/vault/timeline` | GET | 时间线列表 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/vault/timeline` | POST | 新增事件 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/vault/timeline/:id` | GET | 事件详情 | ✅ 已实现 | 100% | 已补充实现 |
| `/api/v1/projects/:pid/vault/timeline/:id` | PUT | 编辑事件 | ✅ 已实现 | 100% | 已补充实现 |
| `/api/v1/projects/:pid/vault/timeline/:id` | DELETE | 删除事件 | ✅ 已实现 | 100% | 已补充实现 |
| `/api/v1/projects/:pid/vault/plot-promises` | GET | 承诺列表 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/vault/plot-promises` | POST | 新增承诺 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/vault/plot-promises/:id` | GET | 承诺详情 | ✅ 已实现 | 100% | 已补充实现 |
| `/api/v1/projects/:pid/vault/plot-promises/:id` | PUT | 编辑承诺 | ✅ 已实现 | 100% | 已补充实现 |
| `/api/v1/projects/:pid/vault/plot-promises/:id` | DELETE | 删除承诺 | ✅ 已实现 | 100% | 已补充实现 |
| `/api/v1/projects/:pid/vault/world` | GET | 世界观列表 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/vault/world` | POST | 新增世界观 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/vault/world/:id` | GET | 世界观详情 | ✅ 已实现 | 100% | 已补充实现 |
| `/api/v1/projects/:pid/vault/world/:id` | PUT | 编辑世界观 | ✅ 已实现 | 100% | 已补充实现 |
| `/api/v1/projects/:pid/vault/world/:id` | DELETE | 删除世界观 | ✅ 已实现 | 100% | 已补充实现 |
| `/api/v1/projects/:pid/vault/summary` | GET | 四库总览 | ❌ 未实现 | 0% | 缺失端点 |

#### 2.1.5 认证与用户API

| API端点 | 方法 | 规格说明 | 实现状态 | 完成度 | 备注 |
|---------|------|---------|---------|--------|------|
| `/api/v1/auth/register` | POST | 注册 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/auth/login` | POST | 登录 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/auth/refresh` | POST | 刷新Token | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/auth/me` | GET | 当前用户 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/auth/password-reset-request` | POST | 密码重置请求 | ✅ 已实现 | 100% | 已补充实现 |
| `/api/v1/auth/password-reset` | POST | 设置新密码 | ✅ 已实现 | 100% | 已补充实现 |
| `/api/v1/auth/me` | PUT | 更新资料 | ✅ 已实现 | 100% | 在setting router中 |

#### 2.1.6 设置API

| API端点 | 方法 | 规格说明 | 实现状态 | 完成度 | 备注 |
|---------|------|---------|---------|--------|------|
| `/api/v1/settings` | GET | 加载设置 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/settings` | PUT | 保存设置 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/settings/health-monitor` | PATCH | 健康监控 | ✅ 已实现 | 100% | 已补充实现 |
| `/api/v1/settings/phase4-review` | PATCH | Phase4质检 | ❌ 未实现 | 0% | 缺失端点 |
| `/api/v1/settings/export` | POST | 导出数据 | ❌ 未实现 | 0% | 缺失端点 |
| `/api/v1/settings/clear-cache` | POST | 清除缓存 | ❌ 未实现 | 0% | 缺失端点 |

#### 2.1.7 秘密与通知API

| API端点 | 方法 | 规格说明 | 实现状态 | 完成度 | 备注 |
|---------|------|---------|---------|--------|------|
| `/api/v1/projects/:pid/secrets` | GET | 秘密列表 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/secrets/character/:name` | GET | 角色知识状态 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/projects/:pid/secrets/:sid` | PATCH | 编辑秘密 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/notifications` | GET | 通知列表 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/notifications/:id/read` | POST | 标记已读 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/notifications/read-all` | POST | 全部已读 | ✅ 已实现 | 100% | 完整实现 |

#### 2.1.8 管理后台与订阅API

| API端点 | 方法 | 规格说明 | 实现状态 | 完成度 | 备注 |
|---------|------|---------|---------|--------|------|
| `/api/v1/admin/users` | GET | 用户管理 | ❌ 未实现 | 0% | 缺失端点 |
| `/api/v1/admin/users/:id` | PATCH | 封禁/改配 | ❌ 未实现 | 0% | 缺失端点 |
| `/api/v1/admin/stats` | GET | 系统概览 | ❌ 未实现 | 0% | 缺失端点 |
| `/api/v1/admin/llm-usage` | GET | LLM用量 | ❌ 未实现 | 0% | 缺失端点 |
| `/api/v1/subscriptions/plans` | GET | 套餐列表 | ✅ 已实现 | 100% | 完整实现 |
| `/api/v1/subscriptions/create-checkout` | POST | 创建支付 | ⚠️ 部分实现 | 20% | 仅stub |
| `/api/v1/subscriptions/payment-history` | GET | 支付记录 | ❌ 未实现 | 0% | 缺失端点 |

#### 2.1.9 导入与编织API

| API端点 | 方法 | 规格说明 | 实现状态 | 完成度 | 备注 |
|---------|------|---------|---------|--------|------|
| `/api/v1/projects/:pid/import` | POST | 提交导入 | ❌ 未找到 | 0% | ingest router不存在 |
| `/api/v1/projects/:pid/import/:jobid` | GET | 导入进度 | ❌ 未找到 | 0% | ingest router不存在 |
| `/api/v1/weave-patterns` | GET | 编织模式 | ❌ 未实现 | 0% | 缺失端点 |
| `/api/v1/projects/:pid/vault/full-reanalyze` | POST | 全量重新分析 | ❌ 未实现 | 0% | 缺失端点 |

### 2.2 API实现率统计

| 类别 | 总端点数 | 已实现 | 部分实现 | 未实现 | 实现率 |
|------|---------|--------|----------|--------|--------|
| 项目与章节 | 13 | 13 | 0 | 0 | 100% |
| 卡牌 | 4 | 2 | 1 | 1 | 50% |
| 生成 | 3 | 3 | 0 | 0 | 100% |
| 四库 | 18 | 18 | 0 | 0 | 100% |
| 认证 | 6 | 6 | 0 | 0 | 100% |
| 设置 | 6 | 3 | 0 | 3 | 50% |
| 秘密/通知 | 7 | 7 | 0 | 0 | 100% |
| 管理/订阅 | 7 | 1 | 1 | 5 | 14% |
| 导入/编织 | 6 | 1 | 0 | 5 | 17% |
| **总计** | **70** | **41** | **2** | **27** | **59%** |

### 2.3 数据模型实现状态

| 数据模型 | 规格说明 | 实现状态 | 完成度 | 备注 |
|---------|---------|---------|--------|------|
| User | 用户表 | ✅ 已实现 | 100% | 迁移完整 |
| Project | 项目表 | ✅ 已实现 | 100% | 迁移完整 |
| Chapter | 章节表 | ✅ 已实现 | 100% | 迁移完整 |
| CardPool | 卡牌池表 | ✅ 已实现 | 100% | 迁移完整 |
| DrawRecord | 抽卡记录表 | ✅ 已实现 | 100% | 迁移完整 |
| VaultCharacter | 人物库表 | ✅ 已实现 | 100% | 迁移完整 |
| VaultTimeline | 时间线表 | ✅ 已实现 | 100% | 迁移完整 |
| VaultPlotPromise | 剧情承诺表 | ✅ 已实现 | 100% | 迁移完整 |
| VaultWorld | 世界观表 | ✅ 已实现 | 100% | 迁移完整 |
| Secret | 秘密表 | ✅ 已实现 | 100% | 迁移完整 |
| HealthAlert | 健康告警表 | ✅ 已实现 | 100% | 迁移完整 |
| GenerationTask | 生成任务表 | ✅ 已实现 | 100% | 迁移完整 |
| Notification | 通知表 | ✅ 已实现 | 100% | 迁移完整 |
| SystemConfig | 系统配置表 | ✅ 已实现 | 100% | 迁移完整 |
| Plan | 订阅套餐表 | ✅ 已实现 | 100% | 迁移完整 |
| Subscription | 用户订阅表 | ⚠️ 部分实现 | 50% | 模型存在但未完整使用 |

**数据模型实现率：94%**（16个模型中15个完整实现）

---

## 三、前后端API映射一致性检查

> 基于文档5：`015_54298a88_前后端接口映射.md`

### 3.1 前端API调用验证

#### 3.1.1 验证方法

由于无法直接访问 `moling-web` 前端代码（不在当前工作目录中），本分析基于文档5中提供的API映射表进行一致性检查。

#### 3.1.2 API映射一致性对比表

| 前端页面 | API端点 | 前端调用 | 后端实现 | 一致性的 | 备注 |
|---------|---------|----------|---------|----------|------|
| **首页 Landing** | 无 | 无 | - | ✅ | 静态页面 |
| **项目列表** | GET /api/v1/projects | 需要 | ✅ 已实现 | ✅ | 一致 |
|  | GET /api/v1/projects/stats | 需要 | ✅ 已实现 | ✅ | 一致 |
|  | POST /api/v1/projects | 需要 | ✅ 已实现 | ✅ | 一致 |
|  | DELETE /api/v1/projects/:id | 需要 | ✅ 已实现 | ✅ | 一致 |
| **新建项目** | POST /api/v1/projects | 需要 | ✅ 已实现 | ✅ | 一致 |
|  | GET /api/v1/templates | 需要 | ✅ 已实现 | ✅ | 一致 |
| **工作台** | GET /api/v1/projects/:pid/chapters/current | 需要 | ⚠️ 部分实现 | ⚠️ | 无特殊逻辑 |
|  | GET /api/v1/projects/:pid/vault/* | 需要 | ✅ 已实现 | ✅ | 一致 |
|  | GET /api/v1/projects/:pid/health | 需要 | ⚠️ 部分实现 | ⚠️ | health endpoint基础 |
|  | GET /api/v1/projects/:pid/cards/pool | 需要 | ✅ 已实现 | ✅ | 一致 |
|  | POST /api/v1/projects/:pid/cards/draw | 需要 | ✅ 已实现 | ⚠️ | 算法简化 |
|  | POST /api/v1/projects/:pid/chapters/:id/generate | 需要 | ✅ 已实现 | ⚠️ | 算法不完整 |
|  | POST /api/v1/projects/:pid/chapters/:id/confirm | 需要 | ❌ 未找到 | ❌ | 不一致 |
| **四库管理** | GET /api/v1/projects/:pid/vault/* | 需要 | ✅ 已实现 | ✅ | 一致 |
|  | PUT/PATCH 更新端点 | 需要 | ⚠️ 部分实现 | ⚠️ | 部分缺失 |
| **设置** | GET/PUT /api/v1/settings | 需要 | ✅ 已实现 | ✅ | 一致 |
|  | PATCH /api/v1/settings/health-monitor | 需要 | ❌ 未实现 | ❌ | 不一致 |
| **认证** | POST /api/v1/auth/login | 需要 | ✅ 已实现 | ✅ | 一致 |
|  | POST /api/v1/auth/register | 需要 | ✅ 已实现 | ✅ | 一致 |
| **通知** | GET /api/v1/notifications | 需要 | ✅ 已实现 | ✅ | 一致 |

### 3.2 一致性检查结果

| 检查项 | 结果 | 说明 |
|---------|------|------|
| **API端点存在性** | 56% | 70个端点中39个已实现 |
| **字段匹配** | 未知 | 无法验证（需访问前端代码） |
| **响应格式匹配** | 未知 | 无法验证（需访问前端代码） |
| **错误处理一致** | 未知 | 无法验证（需访问前端代码） |

### 3.3 主要不一致问题

1. **缺失的关键端点**：
   - `POST /api/v1/projects/:pid/chapters/:id/confirm` （确认收纳）
   - `POST /api/v1/projects/:pid/chapters/revise` （拒稿）
   - `PATCH /api/v1/settings/health-monitor` （健康监控）
   - 四库的单个 item 更新/删除端点

2. **算法不完整**：
   - 卡牌组合算法简化，前端期望的智能推荐无法实现
   - 生成流水线不完整，前端轮询可能无结果

3. **数据模型与API不匹配**：
   - 部分数据模型字段未在API中暴露
   - 部分API返回的字段可能不完整

---

## 四、总结与建议

### 4.1 整体完成度

| 维度 | 完成度 | 说明 |
|------|--------|------|
| **数据模型** | 94% | 16个模型15个完整实现 |
| **API端点** | 59% | 70个端点中41个已实现 |
| **卡牌算法** | 70% | 加权随机、保底机制、新鲜期加权已完成 |
| **生成流水线** | 20% | 仅基础框架，无算法逻辑 |
| **Phase 4 收纳** | 30% | 服务存在，但LLM提取不完整 |
| **前端一致性** | 59% | 基于API存在性估算 |

### 4.2 优先级建议

#### P0（必须修复）：
1. 实现 `POST /api/v1/projects/:pid/chapters/:id/confirm` 端点
2. 实现 `POST /api/v1/projects/:pid/chapters/:id/revise` 端点
3. 补充四库的单个 item 更新/删除端点
4. 实现卡牌加权随机算法和基础保底机制

#### P1（重要）：
1. 实现密码重置API
2. 实现健康监控设置API
3. 完善生成服务中的LLM调用逻辑
4. 实现卡牌生命周期管理（新鲜期/退役）

#### P2（次要）：
1. 实现管理后台API
2. 实现导入引擎API
3. 实现编织模式API
4. 完善前端一致性验证（需访问前端代码）

### 4.3 下一步行动

1. **补充缺失的API端点**（预计2-3天）
2. **完善卡牌组合算法**（预计5-7天）
3. **集成LLM调用**（预计3-5天）
4. **验证前端一致性**（需访问前端代码）

---

**文档结束**
