# moling-server 代码库探索报告

生成时间: 2026-06-13 22:44:40
探索路径: c:\Users\Admin\Desktop\新建文件夹 (2)\moling-server

---

## 二、路由端点详细清单

### 1. Auth Router (/api/v1/auth)

| HTTP方法 | 路径 | 功能描述 |
|---------|------|------------|
| POST | /register | 用户注册 |
| POST | /login | 用户登录 |
| POST | /refresh | 刷新 Token |
| GET | /me | 获取当前用户信息 |
| PUT | /me | 更新用户资料 |
| POST | /logout | 用户登出 |
| POST | /password-reset-request | 请求密码重置 |
| POST | /set-password | 设置新密码 |

### 2. Project Router (/api/v1/projects)

| HTTP方法 | 路径 | 功能描述 |
|---------|------|------------|
| POST | / | 创建项目 |
| GET | / | 列出用户所有项目 |
| GET | /{project_id} | 获取单个项目 |
| PUT | /{project_id} | 更新项目 |
| DELETE | /{project_id} | 删除项目 |
| GET | /{project_id}/stats | 获取项目统计 |
| GET | /suggestions | 获取创作建议 |
| PUT | /{project_id}/draft | 保存为草稿 |
| GET | /{project_id}/health/alerts | 获取健康告警 |
| POST | /{project_id}/health/refresh | 刷新健康检查 |

### 3. Chapter Router (/api/v1/projects/{project_id}/chapters)

| HTTP方法 | 路径 | 功能描述 |
|---------|------|------------|
| POST | / | 创建章节 |
| GET | / | 列出所有章节 |
| GET | /current | 获取当前最新章节 |
| GET | /{chapter_id} | 获取单个章节 |
| PUT | /{chapter_id} | 更新章节 |
| DELETE | /{chapter_id} | 删除章节 |
| POST | /{chapter_id}/confirm | 确认章节 |
| POST | /{chapter_id}/revise | 退回修改 |
| GET | /{chapter_id}/suggestions | 获取章节建议 |
| POST | /{chapter_id}/agent | AI Agent 指令 |
| POST | /{chapter_id}/redraw | 重抽卡片 |

### 4. Generation Router (/api/v1)

| HTTP方法 | 路径 | 功能描述 |
|---------|------|------------|
| POST | /projects/{project_id}/chapters/{chapter_id}/generate | 触发 AI 生成 |
| GET | /generation/{task_id}/status | 获取任务状态 |
| GET | /history?project_id=xxx | 生成历史 |
| POST | /generation/{task_id}/cancel | 取消生成任务 |

### 5. Vault Router (/api/v1/projects/{project_id}/vault)

| HTTP方法 | 路径 | 功能描述 |
|---------|------|------------|
| GET | /characters | 列出所有角色 |
| POST | /characters | 创建角色 |
| PUT | /characters/{character_id} | 更新角色 |
| DELETE | /characters/{character_id} | 删除角色 |
| GET | /timeline | 列出时间线事件 |
| POST | /timeline | 创建时间线事件 |
| GET | /plot-promises | 列出剧情承诺 |
| POST | /plot-promises | 创建剧情承诺 |
| GET | /world | 列出世界观条目 |
| POST | /world | 创建世界观条目 |

### 6. Card Router (/api/v1/projects/{project_id}/cards)

| HTTP方法 | 路径 | 功能描述 |
|---------|------|------------|
| POST | /draw | 抽卡 |
| GET | /history | 抽卡历史 |
| GET | /pool | 卡片池列表 |

## 三、服务层函数详细清单

### 1. ProjectService (project_service.py)

`python
class ProjectService:
    async def create_project(db, user_id, req) -> ProjectResp
    async def get_project(db, project_id, user_id) -> ProjectResp
    async def update_project(db, project_id, user_id, req) -> ProjectResp
    async def delete_project(db, project_id, user_id) -> None
    async def list_user_projects(db, user_id, skip, limit) -> list[ProjectResp]
    async def get_project_stats(db, user_id) -> ProjectStatsResp
`

### 2. ChapterService (chapter_service.py)

`python
class ChapterService:
    async def create_chapter(db, project_id, user_id, req) -> ChapterResp
    async def get_chapter(db, project_id, chapter_id, user_id) -> ChapterResp
    async def update_chapter(db, project_id, chapter_id, user_id, req) -> ChapterResp
    async def delete_chapter(db, project_id, chapter_id, user_id) -> None
    async def confirm_chapter(db, project_id, chapter_id, user_id) -> None
    async def revise_chapter(db, project_id, chapter_id, user_id) -> None
    async def list_chapters(db, project_id, user_id, skip, limit) -> list[ChapterResp]
    async def get_current_chapter(db, project_id, user_id) -> ChapterResp | None
`

### 3. GenerationService (generation_service.py)

`python
class GenerationService:
    async def create_task(db, project_id, chapter_id, user_id, req) -> GenerationResp
    async def execute_generation(db, task_id) -> dict
    async def get_task_status(db, task_id) -> TaskStatusResp
    async def list_task_history(db, project_id, skip, limit) -> list[TaskStatusResp]
    async def cancel_task(db, task_id, user_id) -> None
`

### 4. VaultService (vault_service.py)

`python
class VaultService:
    # Characters
    async def list_characters(db, project_id, user_id) -> list[CharacterResp]
    async def get_character(db, project_id, character_id, user_id) -> CharacterResp
    async def create_character(db, project_id, user_id, data) -> CharacterResp
    async def update_character(db, project_id, character_id, user_id, data) -> CharacterResp
    async def delete_character(db, project_id, character_id, user_id) -> None
    
    # Timeline
    async def list_timeline(db, project_id, user_id) -> list[TimelineResp]
    async def get_timeline_event(db, project_id, event_id, user_id) -> TimelineResp
    async def create_timeline_event(db, project_id, user_id, data) -> TimelineResp
    async def update_timeline_event(db, project_id, event_id, user_id, data) -> TimelineResp
    async def delete_timeline_event(db, project_id, event_id, user_id) -> None
    
    # Plot Promises
    async def list_plot_promises(db, project_id, user_id) -> list[PlotPromiseResp]
    async def get_plot_promise(db, project_id, promise_id, user_id) -> PlotPromiseResp
    async def create_plot_promise(db, project_id, user_id, data) -> PlotPromiseResp
    async def update_plot_promise(db, project_id, promise_id, user_id, data) -> PlotPromiseResp
    async def delete_plot_promise(db, project_id, promise_id, user_id) -> None
    
    # World Entries
    async def list_world_entries(db, project_id, user_id) -> list[WorldResp]
    async def get_world_entry(db, project_id, entry_id, user_id) -> WorldResp
    async def create_world_entry(db, project_id, user_id, data) -> WorldResp
    async def update_world_entry(db, project_id, entry_id, user_id, data) -> WorldResp
    async def delete_world_entry(db, project_id, entry_id, user_id) -> None
`

### 5. CardService (card_service.py)

`python
class CardService:
    # 卡牌生命周期 (E7)
    async def check_freshness(db, card_id, current_chapter) -> dict
    async def check_retirement(db, card_id, current_chapter) -> dict
    async def check_elimination(db, card_id, current_chapter) -> dict
    async def update_card_lifetime(db, card_id, current_chapter) -> dict
    
    # 抽卡状态机 (E8)
    class DrawStateMachine:
        def __init__(self)
        def transition(self, new_state: str) -> bool
        def should_pity(self) -> bool
        def get_weighted_cards(self, db, cards, weights, current_chapter) -> list
    
    async def draw_cards(db, project_id, chapter_id, mode, count) -> dict
    async def redraw_cards(db, project_id, chapter_id, current_card_ids) -> dict
`

### 6. ValidationService (validation_service.py) - 部分 TODO 占位

`python
class ValidationService:
    # 生成前校验 (E9) - 已实现
    async def pre_check(db, project_id, chapter_id, card_ids, weights) -> dict
    
    # 生成后校验 (E10) - 大部分是 TODO 占位
    async def post_check(db, project_id, chapter_id, generated_text) -> dict
    def _check_text_length(text: str) -> dict  # TODO
    async def _check_consistency(db, chapter_id, text) -> dict  # TODO
    async def _check_vault_consistency(db, project_id, text) -> dict  # TODO
    async def _check_secret_conflicts(db, project_id, text) -> dict  # TODO
    async def _check_hooks_advancement(db, project_id, text) -> dict  # TODO
    def _check_style_consistency(text: str) -> dict  # TODO
    def _check_sensitivity(text: str) -> dict  # TODO
`

## 四、数据模型定义详细清单（关键模型）

### 1. Project (models/project.py)

`python
class Project(BaseModel):
    __tablename__ = "projects"
    
    user_id: Mapped[str]  # 所属用户 ID
    title: Mapped[str]  # 作品标题
    author: Mapped[str]  # 作者署名
    genre: Mapped[str]  # 作品类型/题材
    status: Mapped[str]  # draft / active / completed / archived
    chapter_count: Mapped[int]  # 章节数量
    word_count: Mapped[int]  # 当前总字数
    target_words: Mapped[Optional[int]]  # 目标总字数
    
    # Relationships
    chapters = relationship("Chapter", back_populates="project")
`

### 2. Chapter (models/chapter.py)

`python
class Chapter(BaseModel):
    __tablename__ = "chapters"
    
    project_id: Mapped[str]  # 所属项目 ID
    title: Mapped[str]  # 章节标题
    content: Mapped[Optional[str]]  # 章节正文
    chapter_number: Mapped[int]  # 章节序号
    status: Mapped[str]  # draft / generating / completed / revised
    phase4_status: Mapped[str]  # none / pending / running / done / failed
    word_count: Mapped[int]  # 本章字数
    used_card_ids: Mapped[Optional[list]]  # 使用的卡片 ID 列表
    generation_mode: Mapped[Optional[str]]  # 生成模式
`

### 3. CardPool (models/card_pool.py)

`python
class CardPool(BaseModel):
    __tablename__ = "card_pool"
    
    project_id: Mapped[str]  # 所属项目 ID
    name: Mapped[str]  # 卡片名称
    description: Mapped[str]  # 卡片描述
    rarity: Mapped[str]  # common / rare / epic / legendary
    direction_type: Mapped[str]  # 稳妥 / 有趣 / 惊艳 / 神之一手
    direction_text: Mapped[str]  # 方向指示文本
    
    # B13: 算法字段
    rarity_weight: Mapped[Optional[int]]  # 稀有度权重
    characters: Mapped[Optional[list]]  # 关联角色列表
    plot_promises: Mapped[Optional[list]]  # 关联剧情承诺列表
    timeline_point: Mapped[Optional[str]]  # 时间线关键点
    world_rules: Mapped[Optional[list]]  # 关联世界观规则
    current_story_state: Mapped[Optional[str]]  # 当前故事状态
    unresolved_hooks: Mapped[Optional[list]]  # 未收束钩子列表
    dynamic_conflict_score: Mapped[Optional[float]]  # 动态冲突评分
    
    # 生命周期字段
    status: Mapped[str]  # active / retired / archived
    freshness_chapter: Mapped[Optional[int]]  # 新鲜度章节号
    draw_count: Mapped[int]  # 被抽取次数
    remaining_lifetime: Mapped[Optional[int]]  # 剩余寿命
`

### 4. GenerationTask (models/generation_task.py)

`python
class GenerationTask(Base, TimestampMixin):
    __tablename__ = "generation_tasks"
    
    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4())
    project_id: Mapped[int]  # 所属项目 ID
    chapter_id: Mapped[Optional[int]]  # 关联章节 ID
    user_id: Mapped[int]  # 发起任务用户 ID
    task_type: Mapped[str]  # generate / phase4 / revise / analyze
    status: Mapped[str]  # pending / running / done / failed / cancelled
    input_params: Mapped[dict]  # 输入参数 (JSON)
    output_data: Mapped[Optional[dict]]  # 输出数据 (JSON)
    progress_stage: Mapped[Optional[str]]  # 当前进度阶段描述
    progress_percent: Mapped[int]  # 进度百分比
    error_message: Mapped[Optional[str]]  # 错误信息
`

## 五、中间件实现详细清单

### 1. RequestIDMiddleware (middleware/request_id.py)

**功能**: 为每个请求注入唯一标识 X-Request-ID

### 2. ResponseFormatMiddleware (middleware/response_format.py)

**功能**: 统一所有响应的格式为:
`json
{
    "code": 0,
    "message": "success",
    "data": {},
    "meta": {"request_id": "", "timestamp": 0, "version": "", "elapsed_ms": 0}
}
`

### 3. RateLimitMiddleware (middleware/rate_limit.py)

**功能**: API 请求频率限制（基于内存，100次/60秒）

### 4. AuditLogMiddleware (middleware/audit_log.py)

**功能**: 记录所有 API 调用的审计日志（排除 /health, /docs 等路径）

---

## 六、Genre 拆书引擎详细清单

### 位置: app/genre/

| 文件 | 功能 | 状态 |
|------|------|------|
| a1_opening.py | A1 黄金三章结构提取 | 已实现 |
| a2_characters.py | A2 角色出场模式聚类 | 已实现 |
| a3_hooks.py | A3 钩子密度量化 | 已实现 |
| a4_rhythm.py | A4 节奏曲线拟合 | 已实现 |
| a5_profile_output.py | A5 套路归纳 + 去版权化 | 已实现 |
| models.py | GenreProfile 数据模型 | 已实现 |

## 七、Ingest 导入引擎详细清单

### 位置: app/ingest/

### 架构: Phase 0-3 流水线

1. **Phase 0**: 采集与分章 (scraper/)
2. **Phase 1**: 全量四库分析 (phase1/)
3. **Phase 2**: 近三章动态层分析 (phase2/)
4. **Phase 3**: 确认导入 (phase3/)

### Service 层 (service.py) 关键函数

`python
class IngestService:
    # Phase 0
    async def dissect_url(url, split_strategies) -> dict
    async def dissect_html(raw_html, source_url, split_strategies) -> dict
    async def dissect_text(text, title, split_strategies) -> dict
    async def fetch_toc(toc_url, max_chapters) -> dict
    async def batch_crawl(toc_url, max_chapters, split_strategies) -> dict
    
    # Job Management
    async def create_job(db, project_id, user_id, ...) -> IngestJob
    async def get_job(db, job_id) -> IngestJob
    async def get_jobs_for_project(db, project_id) -> list[IngestJob]
    
    # Phase 1-3
    async def run_phase1(db, job_id, chapters_data) -> dict
    async def run_phase2(db, job_id) -> dict
    async def run_phase3(db, job_id, resolve_strategy) -> dict
    
    # 全流程一键导入
    async def full_import(db, project_id, user_id, chapters_data, ...) -> dict
`

## 八、TODO 占位符和未完成功能汇总

### 严重未完成功能

#### 1. ValidationService - 生成后校验 (E10)

文件: `app/service/validation_service.py`

以下方法都是 **TODO 占位**，未实现实际逻辑：

`python
def _check_text_length(self, text: str) -> dict:  # TODO: 实现长度检查
async def _check_consistency(self, db, chapter_id, text) -> dict:  # TODO: 实现连贯性检查
async def _check_vault_consistency(self, db, project_id, text) -> dict:  # TODO: 实现四库一致性检查
async def _check_secret_conflicts(self, db, project_id, text) -> dict:  # TODO: 实现秘密矩阵冲突检查
async def _check_hooks_advancement(self, db, project_id, text) -> dict:  # TODO: 实现钩子推进检查
def _check_style_consistency(self, text: str) -> dict:  # TODO: 实现风格一致性检查
def _check_sensitivity(self, text: str) -> dict:  # TODO: 实现敏感内容检查
`

**影响**: 生成后校验流程完全绕过，无法保证生成内容质量。

#### 2. HealthService - 健康监控

文件: pp/service/health_service.py

以下方法未完全实现：

`python
def _calculate_promise_age(self, promise) -> int:
    # TODO: 需要获取当前章节号（从 context 传入）
    return 5  # 默认 5 章（简化实现）

def _calculate_health_score(self, promises, alerts) -> float:
    # TODO: 实现健康分数计算
    # 当前有框架代码但不完整

async def _save_alert(self, db, project_id, alert) -> None:
    # TODO: 如果后续创建了 HealthAlert 表，可以保存到数据库
    # 当前仅打印到控制台

async def handle_alert_action(self, db, alert_id, action) -> dict:
    # TODO: 更新承诺状态
    # TODO: 设置忽略期限
    # TODO: 不做特殊处理
    # 所有 action 都返回 success 但未实际处理
`

**影响**: 健康监控告警可被触发，但处理结果不持久化。

#### 3. AlgorithmService - 部分 TODO

文件: pp/service/algorithm_service.py

- step8_batch_llm_call: # TODO: 后续可以调用 LLM 来提取约束
- step14_update_vault: # TODO: 如果后续创建了 DynamicLayerArchive 表，可以保存到数据库
- step22_archive_changes: # TODO: 如果后续创建了 Changelog 表，可以保存到数据库

#### 4. PromptService - 四库过滤 TODO

文件: pp/service/prompt_service.py, prompt_service_fixed.py

- _filter_vault_context: # TODO: 实现四库过滤算法 (E5)
- _build_style_prompt: # TODO: 调用 style_prompt_builder.fingerprint_to_prompt()

---

## 九、总结

### 已实现的核心功能

1. **用户认证系统** - AuthService 完整实现
2. **项目管理** - ProjectService 完整实现
3. **章节管理** - ChapterService 完整实现
4. **卡池生命周期** - CardService 完整实现（E7 卡牌生命周期 + E8 抽卡状态机）
5. **生成前校验** - ValidationService.pre_check 完整实现（E9）
6. **四库管理** - VaultService 完整实现
7. **LLM 集成** - LLMClient 完整实现
8. **拆书引擎** - Genre 模块 A1-A5 全部实现
9. **导入引擎** - Ingest 模块 Phase 0-3 全部实现

### 关键未完成功能

1. **生成后校验** - ValidationService.post_check 完全未实现（E10）
2. **健康监控持久化** - HealthService 告警处理未保存到数据库
3. **Phase 4 审核工作流** - 仅有路由骨架，未串联实际算法
4. **四库过滤算法** - PromptService 中的 E5 算法未实现

### 代码质量评估

- **路由层**: 完整，覆盖所有 API 端点
- **服务层**: 核心功能已实现，部分校验逻辑待完成
- **数据模型**: 完整，包含所有必要字段
- **中间件**: 完整实现 4 个中间件
- **拆书引擎**: A1-A5 全部实现，代码质量高
- **导入引擎**: Phase 0-3 全部实现，架构清晰

---

*报告结束*
