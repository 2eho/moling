# 墨灵 (Moling Web) 全局审计报告

> 审计日期：2026-06-12 | 审计范围：后端路由 / 前端映射 / 算法文档一致性
> 审计员：audit-router + audit-frontend + audit-algo 并行作业

---

## 一、总体健康度

| 维度 | 已实现 | 部分实现 | 未实现 | 总计功能点 |
|:-----|:------:|:--------:|:------:|:----------:|
| 后端 API 端点 | 53 | — | ~30 | 约 83 |
| 前端页面路由 | 12/16 | — | 4 | 16 |
| 算法文档功能点 | ~40 (53%) | ~3 (4%) | ~32 (43%) | 约 75 |
| API 映射文档准确性 | ~25/63 | ~8 路径差异 | ~30 缺失 | 63 |

### 关键结论

**后端已实现 53 个端点，但约有 30 个缺失端点、16 个代码独有、30+ 算法功能点未实现。**

---

## 二、P0 — 阻塞性缺陷（必须修复后才能正常工作）

### 2.1 前端 8 处 API 路径指向错误（会导致 404）

| # | 前端函数 (api.ts) | 当前错误路径 | 后端实际路径 | 影响 |
|:-:|:-----------------|:------------|:------------|:----|
| 1 | `cardApi.getPool()` | `/cards/pool?project_id=xxx` | `/api/v1/cards/pool?project_id=xxx` | 卡牌池不显示 |
| 2 | `cardApi.drawCards()` | `/cards/draw?project_id=xxx` | `/api/v1/cards/draw?project_id=xxx` | 抽卡失败 |
| 3 | `cardApi.redraw()` | `/cards/draw` | `/api/v1/cards/draw` | 重抽也是走 draw |
| 4 | `generationApi.generate()` | `/generation/trigger` | `/api/v1/generation/trigger` | 生成无法触发 |
| 5 | `generationApi.getStatus()` | `/generation/task/:taskId` | `/api/v1/generation/task/{task_id}` | 无状态轮询 |
| 6 | `generationApi.cancel()` | `/generation/task/:taskId/cancel` | — (后端缺失此路由) | 取消功能不可用 |
| 7 | `generationApi.confirm()` | `/chapters/:id/confirm` | — (后端缺失此路由) | 确认收纳不可用 |
| 8 | `generationApi.revise()` | `/chapters/:id/revise` | — (后端缺失此路由) | 拒稿重写不可用 |

> 注：实际 API base URL 为 `http://localhost:8000/api/v1`，前端调用略过 base 前缀主要是 apiClient 自动拼接。路径差异主要体现在路由命名层面（如 `generation` vs `generate`、`task/:taskId` vs `task/{task_id}`）

**影响评估**：工作台页面的核心功能（抽卡、生成、确认/拒稿）全无法正常工作。

### 2.2 后端缺失关键章节操作路由

| 缺失路由 | 用途 | 前端依赖 |
|:---------|:-----|:---------|
| `POST /projects/:pid/chapters/:id/confirm` | 确认收纳生成内容 | workspace |
| `POST /projects/:pid/chapters/:id/revise` | 拒稿要求重写 | workspace |
| `POST /projects/:pid/chapters/:id/generate` | 触发生成（替代 `/generation/trigger`） | workspace |
| `POST /projects/:pid/chapters/:id/redraw` | 重抽卡牌 | workspace |
| `POST /generate/:task_id/cancel` | 取消生成任务 | workspace |

---

## 三、P1 — 严重缺口（功能不完整，影响用户体验）

### 3.1 完全无后端的页面

| 页面 | 路由 | 当前状态 | 需实现的 API |
|:----|:-----|:---------|:------------|
| **Settings 设置** | `/settings` | 全部前端 mock | 6 个端点：GET/PUT settings、PATCH health-monitor、PATCH phase4-review、POST export、POST clear-cache |
| **Vault 四库** | `/vaults/[projectId]` | 全部前端 mock | vault PUT 端点 + secrets 端点 |
| **Notifications 通知** | `/notifications` | 全部前端 mock | 3 个通知端点 |
| **Pricing 定价** | `/pricing` | 硬编码套餐 | 2 个订阅端点 |
| **Import 导入** | `/projects/[projectId]/import` | setTimeout mock | ingest 路由已实现，需前端接入 |

### 3.2 生成流水线严重精简（算法缺口）

当前 `worker/tasks.py` 中 `_execute_generation()` 的流程：

```
用户触发生成 → 组装基础 prompt → 一次 LLM 调用 → 返回结果
```

算法文档要求的流程：

```
权重分配(按稀有度) → 四库过滤(卡片ID关联提取) 
→ 动态层冲突检测 → 方向相容性检测 → 编织方案匹配 
→ 大纲模板填充 → 小模型叙事元素提取 → 中模型头脑风暴 
→ 大模型正文写作 → 7步连贯性校验 → 动态层更新
```

**10+ 个算法步骤中只实现了最后 1 个 LLM 调用。**

### 3.3 Phase 4 四库收纳调度器完全缺失

这是从"生成章节"到"四库持续积累"的核心闭环，当前写完后内容无法自动入库：
- 四库变更提取 [14]
- 逐库合并写入 [15]-[18]
- 秘密矩阵提取 [19]
- 卡牌池充实 [20]
- 子情节健康检查 R1/R2/R3 [21]
- 变更日志归档 [22]

### 3.4 Settings 完全缺失（6 API + 前端 mock）

- 后端 6 个 Settings 端点完全未实现
- 前端设置页（AI 模型配置、导出、清除缓存）完全使用本地 state

### 3.5 Vault CRUD 不完整

| 缺失操作 | 说明 |
|:---------|:-----|
| `PUT /vault/characters/:id` | 不能编辑角色 |
| `PUT /vault/plot-promises/:id` | 不能编辑剧情承诺 |
| `GET /vault/summary` | 不能获取四库概览 |
| `POST /vault/full-reanalyze` | 不能触发全量重分析 |

---

## 四、P2 — 中等优先级问题

### 4.1 认证模块缺失端点

| 缺失端点 | 影响 |
|:---------|:-----|
| `PUT /auth/me` | 用户无法更新资料 |
| `POST /auth/password-reset-request` | 无法请求重置密码 |
| `POST /auth/password-reset` | 无法完成密码重置 |

### 4.2 卡牌池算法未实现

| 算法特性 | 当前状态 |
|:---------|:---------|
| 加权随机抽卡 | ❌ 仅 order by random() |
| 分层保底（第1张至少rare） | ❌ |
| 新鲜期加权（×1.5） | ⚠️ 有字段无逻辑 |
| 久未出现加成 | ❌ |
| LRU淘汰检查 | ❌ |
| 重抽次数限制（3次） | ❌ |

### 4.3 LLM 基础设施缺口

| 特性 | 当前状态 | 说明 |
|:-----|:---------|:-----|
| 语义缓存 | ❌ | 算法文档 §2.7 描述，未实现 |
| API Key Pool 轮换 | ❌ | 只用单个 key |
| 模型 Fallback 链 | ❌ | pro→flash→失败链 |
| LiteLLM Proxy 集成 | ❌ | 直调 LLM API |

### 4.4 连贯性校验完全缺失

- 生成前校验（Pre-check）
- 生成后 7 步校验
- R1/R2/R3 子情节健康监控
- 秘密债务模型

### 4.5 健康告警无实际逻辑

- `healthApi.getAlerts()` 返回空数组 `[]`
- `models/health_alert.py` 存在但 SQL 查询规则未实现
- 后端无项目级健康检查路由

### 4.6 方法不统一（PUT vs PATCH）

- 文档要求 PUT，代码实际使用 PATCH
- 影响：project update、chapter update
- 建议：统一使用 PATCH（更符合 REST 语义，更新文档即可）

### 4.7 路径命名空间不统一

| 资源 | 文档路径 | 代码路径 | 建议 |
|:-----|:---------|:---------|:-----|
| 卡牌 | `/projects/:pid/cards/*` | `/cards/*?project_id=xxx` | 统一为路径参数 |
| 生成 | `/generate/*` | `/generation/*` | 统一命名 |
| 导入 | `/projects/:pid/import/*` | `/ingest/*` | 保持 `/ingest/*`，更新文档 |
| 项目统计 | `/projects/:id/stats` | `/projects/stats`（全局） | 路径与范围不一致 |

---

## 五、文档问题

### 5.1 API 映射文档与实际代码差异

- **约 30 个端点**在映射文档中列出但后端未实现
- 映射文档中 **Ingest 路径全部错误**（用 `/import/*` 而非 `/ingest/*`）
- 映射文档中 Card 路径错误（用 `/projects/:pid/cards/*` 而非 `/cards/*`）
- 映射文档中方法混用（PUT vs PATCH）

### 5.2 后端设计文档与实际代码差异

- Phase 4 伪代码完整但无任何实现
- 抽卡保底算法伪代码完整但无实现
- LLM 三层模型 pipeline 伪代码完整但实际只调一次
- 生成流水线伪代码 vs 实际高度简化

### 5.3 overview.md 过时

- 当前 overview.md 是 6月12日 前端交付的快照，未反映后端和算法状态
- 404 页面声称存在但实际 audit-frontend 报告缺失

### 5.4 代码存在但文档未提及

- 16 个路由在代码中实现但任何文档均未列出（主要是 ingest 的 phase 0-3 端点 + admin/llm-config/test）

---

## 六、修复优先级建议

### 第一阶段 — 让核心流程跑通（P0 + 部分 P1）

| # | 任务 | 预估工作量 |
|:-:|:-----|:----------:|
| 1 | 修复前端的 API 路径（补上 `/api/v1` base 前缀映射） | 小 |
| 2 | 后端实现 `chapter/confirm` + `chapter/revise` 路由 | 中 |
| 3 | 后端实现 `generate/cancel` 路由 | 小 |
| 4 | 后端实现 `chapter/generate` + `chapter/redraw` 路由（或保持现有路径） | 中 |
| 5 | 修改前端 apiClient 使用正确路径 | 小 |
| 6 | 统一 API 映射文档与代码路径（更新文档） | 小 |

### 第二阶段 — 补齐关键模块（P1 剩余）

| # | 任务 | 预估工作量 |
|:-:|:-----|:----------:|
| 7 | 实现 Settings 后端 6 个端点 + 前端接入 | 中 |
| 8 | 实现 Vault PUT 端点 + secrets 端点 + 前端接入 | 中 |
| 9 | 实现 Notifications 3 个端点 + 前端接入 | 中 |
| 10 | 实现卡牌池加权算法（加权随机+保底+新鲜期+重抽限制） | 大 |
| 11 | 后端 LlmConfig 增加 Key Pool 轮换 + Fallback | 大 |

### 第三阶段 — 算法完整实现（P2）

| # | 任务 | 预估工作量 |
|:-:|:-----|:----------:|
| 12 | 实现 Phase 4 收纳调度器（含 Redis 锁） | 特大 |
| 13 | 实现生成流水线算法步骤（权重分配→过滤→冲突检测→编织匹配→大纲） | 特大 |
| 14 | 实现连贯性校验（Pre-check + Post-check 7步） | 大 |
| 15 | 实现秘密矩阵生命周期 | 大 |
| 16 | 实现 R1/R2/R3 健康监控 | 中 |

---

## 七、附录：文件引用

| 报告来源 | 原始文件 |
|:---------|:---------|
| 后端路由审计 | `backend/app/routers/*.py` |
| 前端页面审计 | `src/app/*` + `src/lib/api.ts` |
| 算法文档审计 | `docs/009_2b7b5b03_moling-card-combination-algorithm.md` |
| 后端设计文档 | `docs/012_a7c27b64_墨灵后端设计文档.md` |
| 交付总览 | `overview.md` |
