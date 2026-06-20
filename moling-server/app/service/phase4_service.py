"""墨灵 (Moling) — Phase 4 (收纳) Service.

业务逻辑：确认收纳、执行收纳流程、更新四库、更新卡牌池。
需要实现完整的收纳调度器，包括调用 LLM 分析内容、更新动态层、更新四库、更新卡牌池。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import chapter_dao, project_dao, vault_dao, card_dao, phase4_dao, dynamic_layer_dao
from app.service.card_retire_service import card_retire_service
from app.service.merge_service import (
    ConfidenceLevel,
    evaluate_confidence,
    should_auto_apply,
)
from app.errors import ErrorCode, NotFoundError, ValidationError, AppError
from app.models import Chapter, Project, DynamicLayer, VaultCharacter, VaultTimeline, VaultPlotPromise, VaultWorld, CardPool
from app.models.phase4_task import Phase4Task
from app.llm.client import llm_client

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# 四库变更提取 JSON Schema 常量 (§11.5)
# ---------------------------------------------------------------------------
EXTRACTION_SCHEMA = {
    "character_updates": [
        {
            "action": "create|update|status_change|remove",
            "name": "角色名称",
            "changes": ["变更描述"],
            "confidence": 0.95,
        }
    ],
    "timeline_updates": [
        {
            "action": "add|resolve_date|correct",
            "event": "事件描述",
            "day": 16,
            "chapter": 16,
            "participants": ["角色名"],
            "importance": "major|minor",
        }
    ],
    "plot_promise_updates": [
        {
            "action": "create|advance|redeem|cancel|escalate",
            "title": "承诺标题",
            "type": "人物弧光|剧情转折|悬念|关系发展|世界观秘密",
            "status": "active|advancing|redeemed|abandoned",
        }
    ],
    "world_updates": [
        {
            "action": "create|expand|clarify|connect",
            "name": "条目名称",
            "category": "geography|history|system|faction|event",
            "content": "详细内容",
        }
    ],
    "card_pool_entries": [
        {
            "type": "剧情|人物|场景|对话",
            "title": "卡牌标题",
            "description": "卡牌描述",
            "rarity": "common|rare|epic",
            "source_chapter": 16,
        }
    ],
}

# 提取 prompt 的 system prompt
_SYSTEM_EXTRACTION = (
    "你是一个小说分析专家。分析以下新章节的内容，提取它对四库的变更。"
    "请严格按照 JSON 格式输出，不要包含 markdown 代码块标记或其他格式。"
    "你的回答应当使用中文。"
)

# 编辑距离阈值用于角色模糊匹配 (§11.7)
CHARACTER_FUZZY_THRESHOLD = 3
# 卡牌新鲜期章节数 (§11.7)
CARD_FRESHNESS_WINDOW = 3
# 卡牌新鲜期权重倍率 (§11.7)
CARD_FRESHNESS_MULTIPLIER = 1.5


class Phase4Service:
    """Service for Phase 4 storage/收纳 operations."""

    async def confirm_storage(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        chapter_id: int,
        nonce: str,
    ) -> Dict[str, Any]:
        """确认收纳请求，开始执行收纳流程。
        
        Args:
            db: 数据库会话
            user_id: 用户 ID
            project_id: 项目 ID
            chapter_id: 章节 ID
            nonce: 防重复提交的随机数
            
        Returns:
            收纳任务信息
        """
        # 1. 验证项目存在且属于用户
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise AppError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # 2. 验证章节存在且属于项目
        chapter = await chapter_dao.get(db, chapter_id)
        if chapter is None:
            raise NotFoundError(
                error_code=ErrorCode.CHAPTER_NOT_FOUND,
                detail="Chapter not found",
            )
        if chapter.project_id != project_id:
            raise AppError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Chapter does not belong to this project",
            )

        # 3. 检查章节是否有生成内容
        if not chapter.content:
            raise ValidationError(
                error_code=ErrorCode.INVALID_REQUEST,
                detail="Chapter has no content to store",
            )

        # 4. 创建 Phase4Task 记录（替代原来的 GenerationTask）
        # Phase4Task 支持三层幂等性防护：nonce unique 约束、幂等性检查、防止重复提交
        existing_task = await phase4_dao.get_by_nonce(db, nonce)
        if existing_task:
            return {
                "task_id": existing_task.id,
                "status": existing_task.status,
                "message": "该收纳任务已存在",
            }


        task = Phase4Task(
            nonce=nonce,
            project_id=str(project_id),
            chapter_id=str(chapter_id),
            status="pending",
        )
        db.add(task)
        await db.flush()
        await db.refresh(task)

        # 5. 更新章节的 phase4_status
        chapter.phase4_status = "pending"
        await db.commit()

        return {
            "task_id": task.id,
            "status": task.status,
            "message": "收纳任务已创建，正在处理中",
        }

    async def analyze_project(self, project_id: int) -> dict:
        """Phase 4 分析：分析卡池、识别待收纳实体、更新保险库条目。

        在 worker 任务中调用，不依赖外部传入的 db session。

        Returns:
            dict with analysis results
        """
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        SessionLocal = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )

        async with SessionLocal() as db:
            # 1. 验证项目存在
            project = await project_dao.get(db, project_id)
            if project is None:
                raise NotFoundError(
                    error_code=ErrorCode.PROJECT_NOT_FOUND,
                    detail="Project not found",
                )

            # 2. 查询项目卡池
            cards = await card_dao.get_active_cards(db, project_id)

            # 3. 分析卡牌内容，提取实体
            entities: Dict[str, List[Dict[str, Any]]] = {
                "characters": [],
                "locations": [],
                "items": [],
                "events": [],
            }
            seen_names: Dict[str, set] = {
                "characters": set(),
                "locations": set(),
                "items": set(),
                "events": set(),
            }

            for card in cards:
                # 从 card.characters 提取角色实体
                card_chars = card.characters or []
                for char in card_chars:
                    name = ""
                    if isinstance(char, dict):
                        name = char.get("name", "")
                    else:
                        name = str(char)
                    if name and name not in seen_names["characters"]:
                        seen_names["characters"].add(name)
                        entities["characters"].append({
                            "name": name,
                            "source_card_id": card.id,
                            "source_card_name": card.name,
                            "card_rarity": card.rarity,
                        })

                # 从 card.direction_text / description 中提取地點和物品
                text_fields = [
                    card.direction_text or "",
                    card.description or "",
                ]
                full_text = " ".join(text_fields)

                # 简单关键词匹配提取（基础版本）
                location_keywords = ["地", "城", "宫", "殿", "塔", "山", "河", "湖",
                                     "海", "森林", "洞穴", "村", "镇", "市"]
                item_keywords = ["剑", "刀", "盾", "戒", "书", "卷", "药", "石",
                                 "符", "阵", "器", "宝", "杖", "镜"]

                for keyword in location_keywords:
                    idx = full_text.find(keyword)
                    while idx >= 0:
                        # 提取关键词前的 2-6 个字符作为地点名
                        start = max(0, idx - 6)
                        end = min(len(full_text), idx + len(keyword) + 2)
                        candidate = full_text[start:end].strip()
                        if candidate not in seen_names["locations"]:
                            seen_names["locations"].add(candidate)
                            entities["locations"].append({
                                "name": candidate,
                                "source_card_id": card.id,
                            })
                        idx = full_text.find(keyword, idx + 1)

                for keyword in item_keywords:
                    idx = full_text.find(keyword)
                    while idx >= 0:
                        start = max(0, idx - 4)
                        end = min(len(full_text), idx + len(keyword) + 2)
                        candidate = full_text[start:end].strip()
                        if candidate not in seen_names["items"]:
                            seen_names["items"].add(candidate)
                            entities["items"].append({
                                "name": candidate,
                                "source_card_id": card.id,
                            })
                        idx = full_text.find(keyword, idx + 1)

                # 从 card.plot_promises 提取事件实体
                card_promises = card.plot_promises or []
                for promise in card_promises:
                    event_name = ""
                    if isinstance(promise, dict):
                        event_name = promise.get("title", "") or promise.get("description", "")
                    else:
                        event_name = str(promise)
                    if event_name and event_name not in seen_names["events"]:
                        seen_names["events"].add(event_name)
                        entities["events"].append({
                            "name": event_name,
                            "source_card_id": card.id,
                            "source_card_name": card.name,
                        })

            # 4. 计算每个实体的置信度评分
            def _calc_confidence(entity_type: str, entity: dict) -> float:
                base = 0.5
                # 来自稀有度高的卡牌 → 更高置信度
                rarity_map = {"legendary": 0.3, "epic": 0.2, "rare": 0.1, "common": 0.0}
                base += rarity_map.get(entity.get("card_rarity", ""), 0.0)
                # 角色名长度合理（2-4 个字）→ 加分
                if entity_type == "characters":
                    name_len = len(entity.get("name", ""))
                    if 2 <= name_len <= 4:
                        base += 0.1
                return min(base, 1.0)

            for etype in entities:
                for entity in entities[etype]:
                    entity["confidence"] = round(_calc_confidence(etype, entity), 2)

            # 5. 按类型分组并排序（按置信度降序）
            grouped = {}
            for etype, items in entities.items():
                grouped[etype] = sorted(items, key=lambda x: x["confidence"], reverse=True)

            # 6. 更新 Phase4Task 记录（标记分析完成）
            pending_tasks = await phase4_dao.get_by_project(
                db, str(project_id), status="pending"
            )
            for task in pending_tasks:
                task.status = "analyzed"
            await db.commit()

            total_entities = sum(len(v) for v in entities.values())

            return {
                "project_id": project_id,
                "total_cards_analyzed": len(cards),
                "total_entities_found": total_entities,
                "entities_by_type": {
                    etype: len(items)
                    for etype, items in grouped.items()
                },
                "entities": grouped,
                "summary": (
                    f"分析完成：扫描 {len(cards)} 张卡牌，"
                    f"发现 {total_entities} 个实体 "
                    f"（{len(entities['characters'])} 角色 / "
                    f"{len(entities['locations'])} 地点 / "
                    f"{len(entities['items'])} 物品 / "
                    f"{len(entities['events'])} 事件）"
                ),
            }

    async def execute_storage(
        self,
        db: AsyncSession,
        task_id: int,
    ) -> Dict[str, Any]:
        """执行收纳流程（异步任务调用）。
        
        Args:
            db: 数据库会话
            task_id: Phase4Task ID
            
        Returns:
            收纳结果
        """
        # 1. 获取任务
        task = await phase4_dao.get(db, task_id)
        if task is None:
            raise NotFoundError(
                error_code=ErrorCode.GENERATION_TASK_NOT_FOUND,
                detail="Task not found",
            )

        # 2. 更新任务状态为 running
        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        await db.commit()

        # 尝试获取关联章节的 content（Phase4Task 没有 input_params，直接从 chapter 读取）
        chapter = await chapter_dao.get(db, int(task.chapter_id))
        project = await project_dao.get(db, int(task.project_id))

        try:
            if chapter is None or project is None:
                raise ValueError("Chapter or project not found")

            # 3. 调用 LLM 分析章节内容，提取变更
            logger.info(f"Analyzing chapter {chapter.id} content with LLM")
            analysis_result = await self._analyze_chapter_content(
                db, project, chapter
            )

            # 4. 更新动态层（DynamicLayer）
            logger.info(f"Updating dynamic layer for chapter {chapter.id}")
            await self._update_dynamic_layer(
                db, project.id, chapter.id, analysis_result
            )

            # 5. 更新四库（Vault）实体
            logger.info(f"Updating vault entities for project {project.id}")
            await self._update_vault_entities(
                db, project.id, chapter.id, analysis_result,
                chapter_number=chapter.chapter_number,
            )

            # 6. 更新卡牌池（CardPool）权重
            logger.info(f"Updating card pool weights for project {project.id}")
            await self._update_card_pool(
                db, project.id, chapter.id, analysis_result
            )

            # 7. 记录收纳历史（更新章节的 phase4_status）
            chapter.phase4_status = "done"
            task.status = "done"
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(f"Phase 4 storage completed for chapter {chapter.id}")
            return {
                "status": "success",
                "message": "收纳完成",
                "analysis": analysis_result,
            }

        except Exception as e:
            logger.error(f"Phase 4 storage failed: {e}", exc_info=True)
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.now(timezone.utc)
            if chapter:
                chapter.phase4_status = "failed"
            await db.commit()
            raise

    async def _analyze_chapter_content(
        self,
        db: AsyncSession,
        project: Project,
        chapter: Chapter,
    ) -> Dict[str, Any]:
        """调用 LLM 分析章节内容，提取变更。
        
        Returns:
            分析结果，包含：
            - characters: 新增/更新的角色
            - timeline_events: 新增的时间线事件
            - plot_promises: 新增/更新的伏笔
            - world_elements: 新增/更新的世界观元素
            - summary: 章节摘要
            - anchors: 章节锚点（POV、地点、时间）
        """
        # 构建 LLM 提示词
        prompt = self._build_analysis_prompt(project, chapter)
        
        # 调用 LLM
        messages = [
            {"role": "system", "content": "你是一个专业的小说内容分析助手。请分析章节内容，提取关键信息。"},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response = await llm_client.chat(
                messages=messages,
                model=settings.LLM_MODEL,
                temperature=0.3,
                max_tokens=4096,
            )
            
            # 解析 LLM 响应
            content = response["choices"][0]["message"]["content"]
            
            # 尝试解析 JSON
            try:
                # 查找 JSON 部分
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    # 如果不是 JSON，返回原始文本
                    result = {"raw_analysis": content}
            except json.JSONDecodeError:
                result = {"raw_analysis": content}
            
            return result
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}", exc_info=True)
            # 返回空结果，使用默认值
            return {
                "characters": [],
                "timeline_events": [],
                "plot_promises": [],
                "world_elements": [],
                "summary": "",
                "anchors": {},
            }

    def _build_analysis_prompt(
        self,
        project: Project,
        chapter: Chapter,
    ) -> str:
        """构建分析提示词。"""
        prompt = f"""请分析以下小说章节内容，提取关键信息。

项目信息：
- 标题：{project.title}
- 作者：{project.author}
- 类型：{project.genre}
- 简介：{project.synopsis}

章节信息：
- 章节标题：{chapter.title}
- 章节编号：{chapter.chapter_number}

章节内容：
{chapter.content}

请提取以下信息，并以 JSON 格式返回：

1. "characters": 新增或更新的角色列表，每个角色包含：name, role, description, traits, emotion, relationships
2. "timeline_events": 新增的时间线事件列表，每个事件包含：event, description, is_key_event, impact, characters_involved
3. "plot_promises": 新增或更新的伏笔列表，每个伏笔包含：description, type, status, urgency, related_characters
4. "world_elements": 新增或更新的世界观元素列表，每个元素包含：term, description, category, rules
5. "summary": 本章节的内容摘要（200字以内）
6. "anchors": 章节锚点，包含：pov（视点角色）, location（地点）, time（时间）

注意：
- 只提取本章节中首次出现或发生变更的信息
- 如果某类信息没有新增或变更，返回空数组
- 请确保返回的是有效的 JSON 格式
"""
        return prompt

    async def _update_dynamic_layer(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        analysis_result: Dict[str, Any],
    ) -> None:
        """更新动态层（DynamicLayer）。"""
        # 获取或创建动态层
        dynamic_layer = await dynamic_layer_dao.get_by_chapter(db, chapter_id)
        
        if dynamic_layer is None:
            dynamic_layer = DynamicLayer(
                project_id=project_id,
                chapter_id=chapter_id,
            )
            db.add(dynamic_layer)
        
        # 更新摘要
        if "summary" in analysis_result:
            dynamic_layer.summary = analysis_result["summary"]
        
        # 更新锚点
        anchors = analysis_result.get("anchors", {})
        if "pov" in anchors:
            dynamic_layer.anchor_pov = anchors["pov"]
        if "location" in anchors:
            dynamic_layer.anchor_location = anchors["location"]
        if "time" in anchors:
            dynamic_layer.anchor_time = anchors["time"]
        
        # 更新未收束钩子（从分析中提取未解决的悬念）
        plot_promises = analysis_result.get("plot_promises", [])
        unresolved = []
        for promise in plot_promises:
            promise_status = promise.get("status", "dormant")
            if promise_status in ("dormant", "active", "advancing"):
                unresolved.append({
                    "description": promise.get("description", ""),
                    "type": promise.get("type", "mystery"),
                    "status": promise_status,
                    "urgency": promise.get("urgency", 5),
                    "related_characters": promise.get("related_characters", []),
                })
        # 合并已有的未收束钩子（去重）
        existing_hooks = dynamic_layer.unresolved_hooks or []
        existing_desc = {h.get("description") for h in existing_hooks if h.get("description")}
        for hook in unresolved:
            if hook["description"] not in existing_desc:
                existing_hooks.append(hook)
                existing_desc.add(hook["description"])
        # 移除已收束（resolved/abandoned）的钩子
        active_descriptions = {p.get("description") for p in plot_promises
                               if p.get("status") not in ("resolved", "abandoned")}
        existing_hooks = [h for h in existing_hooks
                          if h.get("description") in active_descriptions or h.get("description") not in
                          {p.get("description") for p in plot_promises}]
        dynamic_layer.unresolved_hooks = existing_hooks[-20:]  # 最多保留20个
        
        # 更新最近变更
        recent_changes = dynamic_layer.recent_changes or []
        recent_changes.append({
            "chapter_id": chapter_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "changes": analysis_result,
        })
        # 只保留最近 3 章的变更
        dynamic_layer.recent_changes = recent_changes[-3:]
        
        await db.flush()

    async def _update_vault_entities(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        analysis_result: Dict[str, Any],
        chapter_number: int = 0,
    ) -> None:
        """更新四库（Vault）实体。"""
        # 1. 更新角色库
        for char_data in analysis_result.get("characters", []):
            await self._update_or_create_character(
                db, project_id, char_data
            )
        
        # 2. 更新时间线库
        for event_data in analysis_result.get("timeline_events", []):
            await self._create_timeline_event(
                db, project_id, chapter_id, event_data
            )
        
        # 3. 更新伏笔库
        for promise_data in analysis_result.get("plot_promises", []):
            await self._update_or_create_plot_promise(
                db, project_id, promise_data, chapter_number=chapter_number
            )
        
        # 4. 更新世界观库
        for world_data in analysis_result.get("world_elements", []):
            await self._update_or_create_world_element(
                db, project_id, world_data
            )

    async def _update_or_create_character(
        self,
        db: AsyncSession,
        project_id: int,
        char_data: Dict[str, Any],
    ) -> None:
        """更新或创建角色。"""
        # 查找是否已存在同名角色
        character = await vault_dao.get_character_by_name(
            db, project_id, char_data["name"]
        )
        
        if character is None:
            # 创建新角色
            character = VaultCharacter(
                project_id=project_id,
                name=char_data["name"],
                role=char_data.get("role", "neutral"),
                description=char_data.get("description", ""),
                traits=char_data.get("traits", []),
                emotion=char_data.get("emotion", ""),
                relationships=char_data.get("relationships", {}),
                chapter_count=1,
            )
            db.add(character)
        else:
            # 更新现有角色
            if "description" in char_data:
                character.description = char_data["description"]
            if "traits" in char_data:
                character.traits = char_data["traits"]
            if "emotion" in char_data:
                character.emotion = char_data["emotion"]
            if "relationships" in char_data:
                character.relationships = char_data["relationships"]
            character.chapter_count = (character.chapter_count or 0) + 1
        
        await db.flush()

    async def _create_timeline_event(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        event_data: Dict[str, Any],
    ) -> None:
        """创建时间线事件。"""
        event = VaultTimeline(
            project_id=project_id,
            chapter_number=chapter_id,  # 使用 chapter_id 作为 chapter_number
            event=event_data["event"],
            description=event_data.get("description", ""),
            is_key_event=event_data.get("is_key_event", False),
            impact=event_data.get("impact", ""),
            characters_involved=event_data.get("characters_involved", []),
        )
        db.add(event)
        await db.flush()

    async def _update_or_create_plot_promise(
        self,
        db: AsyncSession,
        project_id: int,
        promise_data: Dict[str, Any],
        chapter_number: int = 0,
    ) -> None:
        """更新或创建伏笔。"""
        # 查找是否已存在相似伏笔
        # 使用多策略匹配：关键词匹配 + 描述重叠 + 角色关联
        description = promise_data.get("description", "")
        promise_type = promise_data.get("type", "")
        related_chars = promise_data.get("related_characters", [])

        # 策略 1: 精确描述匹配（前80字符）
        promise = await vault_dao.find_promise_by_description(
            db, project_id, description[:80]
        )

        # 策略 2: 类型 + 角色关联匹配（精确匹配未命中时）
        if promise is None and related_chars:
            for char_name in related_chars:
                promise = await vault_dao.find_promise_by_type_and_char(
                    db, project_id, promise_type, char_name,
                    ["dormant", "active", "advancing"],
                )
                if promise:
                    break
        
        if promise is None:
            # 创建新伏笔
            promise = VaultPlotPromise(
                project_id=project_id,
                description=promise_data["description"],
                type=promise_data.get("type", "mystery"),
                status=promise_data.get("status", "dormant"),
                urgency=promise_data.get("urgency", 5),
                related_characters=promise_data.get("related_characters", []),
                planted_chapter=chapter_number,  # 从分析结果获取章节编号
                advancement_log=[],
            )
            db.add(promise)
        else:
            # 更新现有伏笔
            if "status" in promise_data:
                promise.status = promise_data["status"]
            if "urgency" in promise_data:
                promise.urgency = promise_data["urgency"]
        
        await db.flush()

    async def _update_or_create_world_element(
        self,
        db: AsyncSession,
        project_id: int,
        world_data: Dict[str, Any],
    ) -> None:
        """更新或创建世界观元素。"""
        # 查找是否已存在同名术语
        world = await vault_dao.get_world_entry_by_term(
            db, project_id, world_data["term"]
        )
        
        if world is None:
            # 创建新世界观元素
            world = VaultWorld(
                project_id=project_id,
                term=world_data["term"],
                description=world_data.get("description", ""),
                category=world_data.get("category", "concept"),
                rules=world_data.get("rules", {}),
                reference_chapters=[],
            )
            db.add(world)
        else:
            # 更新现有世界观元素
            if "description" in world_data:
                world.description = world_data["description"]
            if "rules" in world_data:
                world.rules = world_data["rules"]
        
        await db.flush()

    async def _update_card_pool(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        analysis_result: Dict[str, Any],
    ) -> None:
        """更新卡牌池（CardPool）权重。"""
        # 1. 增加已使用卡牌的权重
        used_card_ids = []
        # 从章节记录中获取使用的卡牌 ID
        chapter = await chapter_dao.get(db, chapter_id)
        if chapter and hasattr(chapter, 'used_card_ids') and chapter.used_card_ids:
            used_card_ids = chapter.used_card_ids
            # 增加已使用卡牌的 weight（增加抽中概率）
            for cid in used_card_ids:
                card = await card_dao.get(db, cid)
                if card:
                    card.draw_count = (card.draw_count or 0) - 1  # 减少 draw_count 提高权重
        
        # 2. 根据分析结果，创建新的卡牌
        # 从角色、事件、伏笔中提取方向，创建新卡牌
        new_cards = []
        
        # 从角色创建卡牌
        for char_data in analysis_result.get("characters", []):
            new_cards.append({
                "name": f"{char_data['name']}的故事",
                "description": f"探索{char_data['name']}的更多故事",
                "rarity": "common",
                "direction_type": "interesting",
                "direction_text": f"围绕{char_data['name']}展开情节",
            })
        
        # 从伏笔创建卡牌
        for promise_data in analysis_result.get("plot_promises", []):
            new_cards.append({
                "name": f"伏笔：{promise_data['description'][:20]}",
                "description": f"回收或推进伏笔：{promise_data['description']}",
                "rarity": "rare",
                "direction_type": "interesting",
                "direction_text": f"处理伏笔：{promise_data['description'][:50]}",
            })
        
        # 创建新卡牌
        for card_data in new_cards:
            card = CardPool(
                project_id=project_id,
                name=card_data["name"],
                description=card_data["description"],
                rarity=card_data["rarity"],
                direction_type=card_data["direction_type"],
                direction_text=card_data["direction_text"],
                is_active=True,
                status="active",
                draw_count=0,
            )
            db.add(card)
        
        await db.flush()

    async def get_storage_status(
        self,
        db: AsyncSession,
        user_id: str,
        task_id: int,
    ) -> Dict[str, Any]:
        """查询收纳任务状态。"""
        task = await phase4_dao.get(db, task_id)
        if task is None:
            raise NotFoundError(
                error_code=ErrorCode.GENERATION_TASK_NOT_FOUND,
                detail="Task not found",
            )
        
        return {
            "task_id": task.id,
            "status": task.status,
            "error_message": task.error_message,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }


    async def get_suggestions(
        self,
        db: AsyncSession,
        chapter_id: int,
    ) -> Dict[str, Any]:
        """获取章节的精修建议。

        分析章节内容 + 四库状态，生成针对性精修建议。
        """
        # 获取章节
        chapter = await chapter_dao.get(db, chapter_id)
        if chapter is None:
            raise NotFoundError(
                error_code=ErrorCode.CHAPTER_NOT_FOUND,
                detail="Chapter not found",
            )

        suggestions = []
        details = {}

        # 1. 检查是否有生成的内容
        if not chapter.content:
            suggestions.append({
                "id": "no_content",
                "type": "warning",
                "title": "章节内容为空",
                "description": "当前章节没有正文内容，请先生成内容。",
                "priority": "high",
            })
            return {
                "chapter_id": chapter_id,
                "suggestions": suggestions,
                "overall_score": 0.0,
                "details": details,
            }

        # 2. 分析字数
        word_count = chapter.word_count or len(chapter.content)
        details["word_count"] = word_count
        if word_count < 500:
            suggestions.append({
                "id": "length_too_short",
                "type": "length",
                "title": "章节长度偏短",
                "description": f"本章 {word_count} 字，建议扩展到 1500-3000 字。",
                "priority": "medium",
            })

        # 3. 分析角色出场情况
        try:
            characters = await vault_dao.get_characters(db, chapter.project_id)
            active_chars = [c for c in characters if c.status == "active"]
            details["character_count"] = len(active_chars)
            if len(active_chars) > 5:
                suggestions.append({
                    "id": "too_many_characters",
                    "type": "character",
                    "title": "活跃角色较多",
                    "description": f"当前有 {len(active_chars)} 个活跃角色，注意避免角色过多导致读者混淆。",
                    "priority": "low",
                })
        except Exception:
            pass

        # 4. 分析伏笔状态
        try:
            promises = await vault_dao.get_plot_promises(db, chapter.project_id)
            dormant = [p for p in promises if p.status == "dormant"]
            details["dormant_promises"] = len(dormant)
            if dormant:
                suggestions.append({
                    "id": "dormant_promises",
                    "type": "plot",
                    "title": "休眠伏笔提醒",
                    "description": f"有 {len(dormant)} 个伏笔处于休眠状态，考虑在本章或后续章节回收。",
                    "priority": "high" if len(dormant) > 3 else "medium",
                })
        except Exception:
            pass

        # 5. 计算总体评分
        overall_score = 1.0
        penalty_map = {
            "no_content": -1.0,
            "length_too_short": -0.3,
            "too_many_characters": -0.1,
        }
        for s in suggestions:
            overall_score += penalty_map.get(s["id"], 0.0)
        overall_score = max(0.0, min(1.0, overall_score))
        details["overall_score"] = round(overall_score, 2)

        return {
            "chapter_id": chapter_id,
            "suggestions": suggestions,
            "overall_score": round(overall_score, 2),
            "details": details,
        }

    async def apply_suggestions(
        self,
        db: AsyncSession,
        req: Any,  # ApplyPhase4Req from schemas
    ) -> Dict[str, Any]:
        """应用精修建议到章节。

        根据用户选择的建议类型，执行对应的精修操作。
        """
        chapter_id = req.chapter_id
        suggestion_ids = req.suggestion_ids
        auto_apply = req.auto_apply

        chapter = await chapter_dao.get(db, chapter_id)
        if chapter is None:
            raise NotFoundError(
                error_code=ErrorCode.CHAPTER_NOT_FOUND,
                detail="Chapter not found",
            )

        applied = []
        skipped = []

        for sid in suggestion_ids:
            if sid == "no_content":
                skipped.append({"id": sid, "reason": "无法自动修复，请在生成后重试"})
            elif sid == "length_too_short":
                # 标记为需要扩展（具体扩展由 generation 模块处理）
                chapter.generation_prompt = (
                    (chapter.generation_prompt or "")
                    + "\n[Phase4] 建议扩展本文字数至 1500+"
                )
                applied.append({"id": sid, "action": "标记为需扩展章节"})
            elif sid == "too_many_characters":
                applied.append({"id": sid, "action": "已记录角色密度提醒"})
            elif sid == "dormant_promises":
                applied.append({"id": sid, "action": "已标记伏笔回收建议"})
            else:
                skipped.append({"id": sid, "reason": "未知建议类型"})

        if auto_apply:
            chapter.phase4_status = "done"
        else:
            chapter.phase4_status = "running"

        await db.commit()

        return {
            "success": True,
            "chapter_id": chapter_id,
            "applied_count": len(applied),
            "skipped_count": len(skipped),
            "applied": applied,
            "skipped": skipped,
        }

    async def get_task_status(
        self,
        db: AsyncSession,
        task_id: int,
    ) -> Dict[str, Any]:
        """查询 Phase 4 任务状态（兼容 Phase4TaskResp schema）。"""
        task = await phase4_dao.get(db, task_id)
        if task is None:
            raise NotFoundError(
                error_code=ErrorCode.GENERATION_TASK_NOT_FOUND,
                detail="Task not found",
            )

        return {
            "id": task.id,
            "nonce": task.nonce,
            "project_id": task.project_id,
            "chapter_id": task.chapter_id,
            "status": task.status,
            "error_message": task.error_message,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat() if hasattr(task, 'created_at') and task.created_at else None,
        }

    async def list_chapter_tasks(
        self,
        db: AsyncSession,
        chapter_id: int,
    ) -> list:
        """查询章节的所有 Phase 4 任务。"""
        tasks = await phase4_dao.get_by_chapter(db, str(chapter_id))
        return [
            {
                "id": t.id,
                "nonce": t.nonce,
                "project_id": t.project_id,
                "chapter_id": t.chapter_id,
                "status": t.status,
                "error_message": t.error_message,
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "created_at": t.created_at.isoformat() if hasattr(t, 'created_at') and t.created_at else None,
            }
            for t in tasks
        ]

    async def list_project_tasks(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> list:
        """查询项目的所有 Phase 4 任务。"""
        tasks = await phase4_dao.get_by_project(db, str(project_id))
        return [
            {
                "id": t.id,
                "nonce": t.nonce,
                "project_id": t.project_id,
                "chapter_id": t.chapter_id,
                "status": t.status,
                "error_message": t.error_message,
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "created_at": t.created_at.isoformat() if hasattr(t, 'created_at') and t.created_at else None,
            }
            for t in tasks
        ]


    # ==================================================================
    # §11.4-§11.7 Phase 4 核心服务方法
    # ==================================================================

    async def run_phase4(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        chapter_text: str,
        card_ids: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Phase 4 主入口：执行完整的四库变更提取与合并流程。

        Args:
            db: 数据库会话
            project_id: 项目 ID
            chapter_id: 章节 ID
            chapter_text: 新章节正文
            card_ids: 本次使用的灵感卡 ID 列表（可选）

        Returns:
            包含变更摘要的结果字典
        """
        logger.info(
            f"Starting Phase 4 for project={project_id}, chapter={chapter_id}"
        )

        # 获取当前章节编号
        chapter = await chapter_dao.get(db, chapter_id)
        chapter_number = chapter.chapter_number if chapter else 0

        result: Dict[str, Any] = {
            "version": "",
            "chapter": chapter_number,
            "changes": {
                "characters": {"created": [], "updated": [], "status_changed": []},
                "timeline": {"added": 0},
                "plot_promises": {"created": 0, "advanced": 0, "redeemed": 0},
                "world": {"created": 0, "expanded": 0},
                "card_pool": {"added": 0},
            },
            "summary": "",
        }

        # ── Phase 4 主事务（外层事务） ──────────────────────────────────
        # LLM 调用和解析在事务外（不消耗事务资源）
        # 四库合并 + 卡牌充实 + 卡牌淘汰 + 变更日志在 savepoint 内
        try:
            # 步骤 [14]: LLM 调用 — 事务外（可重试，不消耗事务资源）
            logger.info("Step [14]: Building extraction prompt and calling LLM")
            extraction_result = await self._call_extraction_llm(
                db, project_id, chapter_text, card_ids or []
            )
            parsed = self._parse_extraction_result(extraction_result)

            # ── savepoint：包含所有 DB 写入操作 ──────────────────────
            # savepoint 失败时回滚 savepoint，不中断主事务
            sp = await db.begin_nested()
            try:
                # 步骤 [15]: 合并人物库变更
                logger.info("Step [15]: Merging character updates")
                char_result = await self._merge_characters(
                    db, project_id, parsed.get("character_updates", []),
                    chapter_number=chapter_number,
                )
                result["changes"]["characters"] = char_result

                # 步骤 [16]: 合并时间线库变更
                logger.info("Step [16]: Merging timeline updates")
                timeline_result = await self._merge_timeline(
                    db, project_id, parsed.get("timeline_updates", []),
                    chapter_id=chapter_id, chapter_number=chapter_number,
                )
                result["changes"]["timeline"] = timeline_result

                # 步骤 [17]: 合并剧情承诺库变更
                logger.info("Step [17]: Merging plot promise updates")
                promise_result = await self._merge_plot_promises(
                    db, project_id, parsed.get("plot_promise_updates", []),
                    chapter_number=chapter_number,
                )
                result["changes"]["plot_promises"] = promise_result

                # 步骤 [18]: 合并世界观库变更
                logger.info("Step [18]: Merging world updates")
                world_result = await self._merge_world(
                    db, project_id, parsed.get("world_updates", []),
                    chapter_number=chapter_number,
                )
                result["changes"]["world"] = world_result

                # 步骤 [18a]: 置信度评估（P1-4）
                logger.info("Step [18a]: Evaluating confidence levels")
                confidence_result = self._evaluate_phase4_confidence(
                    result["changes"],
                )
                result["confidence"] = confidence_result

                # 步骤 [19]: 充实卡牌池
                logger.info("Step [19]: Enriching card pool")
                card_result = await self._enrich_card_pool(
                    db, project_id, parsed.get("card_pool_entries", []),
                    chapter_number=chapter_number,
                )
                result["changes"]["card_pool"] = card_result

                # 构建 version 和 summary
                timestamp = int(datetime.now(timezone.utc).timestamp())
                version = f"v4_ch{chapter_number}_{timestamp}"
                result["version"] = version

                summary_parts = []
                if char_result.get("created"):
                    summary_parts.append(f"新增角色 {len(char_result['created'])} 个")
                if char_result.get("updated"):
                    summary_parts.append(f"更新角色 {len(char_result['updated'])} 个")
                if char_result.get("status_changed"):
                    summary_parts.append(f"角色状态变更 {len(char_result['status_changed'])} 个")
                if timeline_result.get("added", 0) > 0:
                    summary_parts.append(f"新增时间线事件 {timeline_result['added']} 个")
                if promise_result.get("created", 0) > 0:
                    summary_parts.append(f"新增伏笔 {promise_result['created']} 个")
                if promise_result.get("advanced", 0) > 0:
                    summary_parts.append(f"推进伏笔 {promise_result['advanced']} 个")
                if world_result.get("created", 0) > 0:
                    summary_parts.append(f"新增世界设定 {world_result['created']} 个")
                if card_result.get("added", 0) > 0:
                    summary_parts.append(f"新增卡牌 {card_result['added']} 张")

                summary = "、".join(summary_parts) if summary_parts else "无变更"
                result["summary"] = summary

                # 步骤 [20]: 归档变更日志（savepoint 内）
                logger.info("Step [20]: Archiving changelog")
                await self._archive_changelog(
                    db, project_id, chapter_id, version, chapter_number, result["changes"],
                )

                # 步骤 [21]: 卡牌淘汰检查（savepoint 内，错误降级）
                try:
                    retire_result = await card_retire_service.check_and_retire(
                        db, project_id, current_chapter=chapter_number,
                    )
                    if retire_result.retired_count > 0:
                        logger.info(
                            f"Card retire: {retire_result.retired_count} retired, "
                            f"{retire_result.expired_count} expired, "
                            f"{retire_result.remaining_active} remaining"
                        )
                        result["card_retire"] = {
                            "retired_count": retire_result.retired_count,
                            "expired_count": retire_result.expired_count,
                            "remaining_active": retire_result.remaining_active,
                        }
                except Exception as retire_err:
                    logger.error(
                        f"Card retire check failed (degraded): {retire_err}",
                        exc_info=True,
                    )

                # 保存 savepoint — 所有合并操作一起提交
                await sp.commit()

            except Exception as e:
                # savepoint 回滚：合并失败不影响主事务
                await sp.rollback()
                logger.error(
                    f"Phase 4 savepoint rollback: merge operations failed: {e}",
                    exc_info=True,
                )
                result["summary"] = f"合并操作失败，已回滚: {str(e)}"

            # 步骤 [22]: 提交主事务
            # savepoint 内的写入已由 sp.commit() 提交到主事务
            # db.commit() 将所有变更持久化到数据库
            await db.commit()
            logger.info(f"Phase 4 completed: {result.get('summary', '')}")

        except Exception as e:
            # 主事务完全回滚（包括 savepoint 已提交的部分）
            await db.rollback()
            logger.error(f"Phase 4 full rollback: {e}", exc_info=True)
            result["summary"] = f"Phase 4 执行出错: {str(e)}"
            # 不抛出异常，保持优雅降级（不改变返回值行为）

        return result

    # ------------------------------------------------------------------
    # §11.5: Prompt 构建
    # ------------------------------------------------------------------

    async def _build_extraction_prompt(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_text: str,
        card_ids: list,
    ) -> str:
        """构建四库变更提取 LLM prompt (§11.5)。"""
        vault_summary = await self._get_vault_summary_async(db, project_id)

        prompt = f"""你是一个小说分析专家。分析以下新章节的内容，提取它对四库的变更。

当前四库上下文：
{vault_summary}

新章节正文：
{chapter_text}

本次使用的灵感卡 ID：
{card_ids}

请输出 JSON，格式如下：

{json.dumps(EXTRACTION_SCHEMA, ensure_ascii=False, indent=2)}

注意：
- character_updates.changes 字段描述具体的变更内容（如"新增","性格由X变为Y","状态由active变为deceased"等）
- timeline_updates 中 day 字段为绝对时间线天数
- plot_promise_updates.type 的枚举值为：人物弧光、剧情转折、悬念、关系发展、世界观秘密
- world_updates.category 的枚举值为：geography、history、system、faction、event
- card_pool_entries.rarity 的枚举值为：common、rare、epic
- 只提取本章节中首次出现或发生变更的信息
- 如果某类信息没有新增或变更，返回空数组
- 请确保返回的是有效的 JSON 格式，不要包含 markdown 代码块标记"""
        return prompt

    async def _get_vault_summary_async(
        self, db: AsyncSession, project_id: int
    ) -> str:
        """异步获取四库的摘要信息（各库的 ID 和名称列表）。"""
        vault_summary_parts = []

        # 获取角色库
        try:
            characters = await vault_dao.get_characters(db, project_id)
            if characters:
                char_list = [
                    f"  - ID: {c.id}, 名称: {c.name}" for c in characters
                ]
                vault_summary_parts.append(
                    "人物库：\n" + "\n".join(char_list)
                )
            else:
                vault_summary_parts.append("人物库：(空)")
        except Exception as e:
            logger.warning(f"Failed to fetch characters: {e}")
            vault_summary_parts.append("人物库：(加载失败)")

        # 获取时间线库
        try:
            timeline = await vault_dao.get_timeline(db, project_id)
            if timeline:
                tl_list = [
                    f"  - ID: {t.id}, 事件: {t.event}, 章节: ch{t.chapter_number}"
                    for t in timeline[-10:]
                ]
                vault_summary_parts.append(
                    "时间线库（最近10条）：\n" + "\n".join(tl_list)
                )
            else:
                vault_summary_parts.append("时间线库：(空)")
        except Exception as e:
            logger.warning(f"Failed to fetch timeline: {e}")
            vault_summary_parts.append("时间线库：(加载失败)")

        # 获取剧情承诺库
        try:
            promises = await vault_dao.get_plot_promises(db, project_id)
            if promises:
                p_list = [
                    f"  - ID: {p.id}, 描述: {p.description[:50]}, 状态: {p.status}"
                    for p in promises[-10:]
                ]
                vault_summary_parts.append(
                    "剧情承诺库（最近10条）：\n" + "\n".join(p_list)
                )
            else:
                vault_summary_parts.append("剧情承诺库：(空)")
        except Exception as e:
            logger.warning(f"Failed to fetch plot promises: {e}")
            vault_summary_parts.append("剧情承诺库：(加载失败)")

        # 获取世界观库
        try:
            world = await vault_dao.get_world_entries(db, project_id)
            if world:
                w_list = [
                    f"  - ID: {w.id}, 名称: {w.name}, 类别: {w.category}"
                    for w in world[-10:]
                ]
                vault_summary_parts.append(
                    "世界观库（最近10条）：\n" + "\n".join(w_list)
                )
            else:
                vault_summary_parts.append("世界观库：(空)")
        except Exception as e:
            logger.warning(f"Failed to fetch world entries: {e}")
            vault_summary_parts.append("世界观库：(加载失败)")

        return "\n".join(vault_summary_parts)

    # ------------------------------------------------------------------
    # §11.5: LLM 调用
    # ------------------------------------------------------------------

    async def _call_extraction_llm(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_text: str,
        card_ids: list,
    ) -> str:
        """调用 LLM 提取四库变更。"""
        # 使用 _build_extraction_prompt 构建 prompt
        prompt = await self._build_extraction_prompt(
            db, project_id, chapter_text, card_ids
        )

        messages = [
            {"role": "system", "content": _SYSTEM_EXTRACTION},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await llm_client.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
            )
            content = response["choices"][0]["message"]["content"]
            logger.info(
                f"LLM extraction response received, length={len(content)}"
            )
            return content
        except Exception as e:
            logger.error(f"LLM extraction call failed: {e}", exc_info=True)
            # 优雅降级：返回空提取结果
            return json.dumps(
                {
                    "character_updates": [],
                    "timeline_updates": [],
                    "plot_promise_updates": [],
                    "world_updates": [],
                    "card_pool_entries": [],
                }
            )

    # ------------------------------------------------------------------
    # §11.5: 解析 LLM 返回的 JSON
    # ------------------------------------------------------------------

    def _parse_extraction_result(self, raw: str) -> Dict[str, List]:
        """解析 LLM 返回的 JSON 提取结果。"""
        if not raw or not raw.strip():
            logger.warning("Empty extraction result from LLM")
            return self._empty_extraction_result()

        # 清理 markdown 代码块标记
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # 移除开头的 ```json 或 ``` 行
            first_newline = cleaned.find("\n")
            if first_newline >= 0:
                cleaned = cleaned[first_newline + 1:]  # +1 跳过换行符
            # 移除结尾的 ``` 行
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        try:
            # 尝试直接解析为 JSON
            if cleaned.startswith("{"):
                result = json.loads(cleaned)
            else:
                # 尝试提取 JSON 部分（处理 LLM 可能的额外文本）
                json_start = cleaned.find("{")
                json_end = cleaned.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = cleaned[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    logger.warning("No JSON found in LLM response")
                    return self._empty_extraction_result()
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse extraction JSON: {e}")
            logger.debug(f"Raw response: {raw[:500]}")
            return self._empty_extraction_result()

        # 验证并规范化结果
        validated: Dict[str, List] = {}
        validated["character_updates"] = result.get("character_updates", [])
        validated["timeline_updates"] = result.get("timeline_updates", [])
        validated["plot_promise_updates"] = result.get("plot_promise_updates", [])
        validated["world_updates"] = result.get("world_updates", [])
        validated["card_pool_entries"] = result.get("card_pool_entries", [])

        # 确保每个条目都是 dict
        for key in validated:
            validated[key] = [
                item for item in validated[key] if isinstance(item, dict)
            ]

        logger.info(
            f"Parsed extraction: "
            f"{len(validated['character_updates'])} characters, "
            f"{len(validated['timeline_updates'])} timeline events, "
            f"{len(validated['plot_promise_updates'])} plot promises, "
            f"{len(validated['world_updates'])} world entries, "
            f"{len(validated['card_pool_entries'])} card entries"
        )
        return validated

    @staticmethod
    def _empty_extraction_result() -> Dict[str, List]:
        """返回空的提取结果。"""
        return {
            "character_updates": [],
            "timeline_updates": [],
            "plot_promise_updates": [],
            "world_updates": [],
            "card_pool_entries": [],
        }

    # ------------------------------------------------------------------
    # §11.7 [15]: 人物库合并
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_edit_distance(s1: str, s2: str) -> int:
        """计算两个字符串之间的编辑距离（Levenshtein）。"""
        if len(s1) < len(s2):
            s1, s2 = s2, s1
        if not s2:
            return len(s1)

        prev_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2):
                cost = 0 if c1 == c2 else 1
                curr_row.append(
                    min(
                        curr_row[j] + 1,         # 删除
                        prev_row[j + 1] + 1,     # 插入
                        prev_row[j] + cost,       # 替换
                    )
                )
            prev_row = curr_row
        return prev_row[-1]

    async def _merge_characters(
        self,
        db: AsyncSession,
        project_id: int,
        updates: List[Dict],
        chapter_number: int = 0,
    ) -> Dict[str, List]:
        """合并人物库变更。

        实现 §11.7 [15]：
        - create → 检查模糊匹配(name编辑距离<3→update,否则新角色)
        - update → 变更历史
        - status_change → 历史状态栈
        - remove → 标记退场
        """
        created: List[Dict] = []
        updated: List[Dict] = []
        status_changed: List[Dict] = []

        # 获取当前项目的所有角色（用于模糊匹配）
        all_characters = await vault_dao.get_characters(db, project_id)
        char_name_map: Dict[str, VaultCharacter] = {c.name: c for c in all_characters}

        for update in updates:
            action = update.get("action", "")
            name = update.get("name", "")
            confidence = update.get("confidence", 0.8)
            changes = update.get("changes", [])

            if not name:
                continue

            if action == "create":
                # 检查模糊匹配：编辑距离 < 3 → 视为同一个角色，执行 update
                matched_char = None
                matched_name = ""
                for existing_name in char_name_map:
                    dist = self._calc_edit_distance(name, existing_name)
                    if dist < CHARACTER_FUZZY_THRESHOLD:
                        if matched_char is None or dist < self._calc_edit_distance(
                            name, matched_name
                        ):
                            matched_char = char_name_map[existing_name]
                            matched_name = existing_name

                if matched_char is not None:
                    # 模糊匹配成功 → update 已有角色
                    update_fields: Dict[str, Any] = {}
                    for change in changes:
                        if isinstance(change, dict):
                            for key in ("role", "faction", "location", "current_state",
                                        "motivation", "description", "personality"):
                                if key in change:
                                    update_fields[key] = change[key]
                        elif isinstance(change, str) and ":" in change:
                            key_val = change.split(":", 1)
                            if len(key_val) == 2:
                                update_fields[key_val[0].strip()] = key_val[1].strip()

                    if update_fields or changes:
                        update_fields["chapter_count"] = (
                            matched_char.chapter_count or 0
                        ) + 1
                        await vault_dao.update_character(
                            db, matched_char, update_fields
                        )
                        updated.append({
                            "id": str(matched_char.id),
                            "name": matched_name,
                            "changes": changes,
                        })
                        logger.info(
                            f"Character fuzzy matched: '{name}' → '{matched_name}' "
                            f"(edit_distance={self._calc_edit_distance(name, matched_name)})"
                        )
                else:
                    # 真正的创建新角色
                    new_char = await vault_dao.create_character(
                        db,
                        {
                            "project_id": project_id,
                            "name": name,
                            "role": self._extract_change(changes, "role", "neutral"),
                            "faction": self._extract_change(changes, "faction", ""),
                            "location": self._extract_change(changes, "location", ""),
                            "current_state": self._extract_change(changes, "current_state", ""),
                            "motivation": self._extract_change(changes, "motivation", ""),
                            "description": self._extract_change(changes, "description", ""),
                            "personality": self._extract_change(changes, "personality", ""),
                            "confidence": confidence,
                            "chapter_count": 1,
                            "chapter_hist": [chapter_number] if chapter_number else [],
                        },
                    )
                    created.append({
                        "id": str(new_char.id),
                        "name": name,
                    })
                    logger.info(f"Character created: {name}")

            elif action in ("update",):
                # 更新已有角色
                if name in char_name_map:
                    existing = char_name_map[name]
                    update_fields = {}
                    for change in changes:
                        if isinstance(change, dict):
                            for key in (
                                "role", "faction", "location", "current_state",
                                "motivation", "description", "personality", "emotion",
                                "traits", "relationships",
                            ):
                                if key in change:
                                    update_fields[key] = change[key]
                        elif isinstance(change, str) and ":" in change:
                            key_val = change.split(":", 1)
                            if len(key_val) == 2:
                                update_fields[key_val[0].strip()] = key_val[1].strip()

                    if update_fields:
                        update_fields["chapter_count"] = (
                            existing.chapter_count or 0
                        ) + 1
                        await vault_dao.update_character(db, existing, update_fields)
                        updated.append({
                            "id": str(existing.id),
                            "name": name,
                            "changes": changes,
                        })
                        logger.info(f"Character updated: {name}")

            elif action == "status_change":
                # 状态变更 → 入历史状态栈
                if name in char_name_map:
                    existing = char_name_map[name]
                    old_status = existing.status
                    new_status = self._extract_change(changes, "status", "inactive")

                    # 保存到 state_machine
                    state_machine = existing.state_machine or {}
                    state_history = state_machine.get("history", [])
                    state_history.append({
                        "from": old_status,
                        "to": new_status,
                        "chapter": chapter_number,
                        "reason": changes if isinstance(changes, str) else str(changes),
                    })
                    state_machine["history"] = state_history
                    state_machine["current"] = new_status

                    await vault_dao.update_character(
                        db,
                        existing,
                        {
                            "status": new_status,
                            "state_machine": state_machine,
                        },
                    )
                    status_changed.append({
                        "id": str(existing.id),
                        "name": name,
                        "from": old_status,
                        "to": new_status,
                    })
                    logger.info(f"Character status changed: {name}: {old_status} → {new_status}")

            elif action == "remove":
                # 标记退场（不物理删除）
                if name in char_name_map:
                    existing = char_name_map[name]
                    await vault_dao.update_character(
                        db, existing, {"status": "deceased"}
                    )
                    status_changed.append({
                        "id": str(existing.id),
                        "name": name,
                        "from": existing.status,
                        "to": "deceased",
                    })
                    logger.info(f"Character marked as deceased: {name}")

        return {
            "created": created,
            "updated": updated,
            "status_changed": status_changed,
        }

    @staticmethod
    def _extract_change(changes: list, key: str, default: Any = None) -> Any:
        """从 changes 列表中提取指定 key 的值。"""
        for change in changes:
            if isinstance(change, dict) and key in change:
                return change[key]
            if isinstance(change, str) and change.startswith(f"{key}:"):
                return change.split(":", 1)[1].strip()
        return default

    # ------------------------------------------------------------------
    # §11.7 [16]: 时间线库合并
    # ------------------------------------------------------------------

    async def _merge_timeline(
        self,
        db: AsyncSession,
        project_id: int,
        updates: List[Dict],
        chapter_id: int = 0,
        chapter_number: int = 0,
    ) -> Dict[str, int]:
        """合并时间线库变更。

        实现 §11.7 [16]：
        - add → 按 day 排序
        - resolve_date → 绑定时间
        - correct → 修正+存档
        """
        added = 0

        for update in updates:
            action = update.get("action", "add")

            if action == "add":
                event = update.get("event", "")
                if not event:
                    continue

                await vault_dao.create_timeline_event(
                    db,
                    {
                        "project_id": project_id,
                        "event": event,
                        "description": (
                            update.get("description") or update.get("event", "")
                        ),
                        "day": update.get("day"),
                        "chapter_number": chapter_number,
                        "source_chapter": chapter_number,
                        "importance": update.get("importance", "minor"),
                        "characters_involved": update.get("participants", []),
                        "is_key_event": update.get("importance") == "major",
                    },
                )
                added += 1
                logger.info(f"Timeline event added: {event[:50]}")

            elif action in ("resolve_date", "correct"):
                # 通过事件名称查找并更新时间
                event_name = update.get("event", "")
                if not event_name:
                    continue
                try:
                    all_events = await vault_dao.get_timeline(db, project_id)
                    target = None
                    for evt in all_events:
                        if evt.event == event_name:
                            target = evt
                            break
                    if target:
                        update_fields = {}
                        if update.get("day") is not None:
                            update_fields["day"] = update["day"]
                        if action == "correct" and update.get("description"):
                            update_fields["description"] = update["description"]
                        if update_fields:
                            await vault_dao.update_timeline_event(
                                db, target, update_fields
                            )
                            logger.info(
                                f"Timeline event {action}: {event_name[:50]}"
                            )
                except Exception as e:
                    logger.warning(
                        f"Failed to {action} timeline event '{event_name}': {e}"
                    )

        return {"added": added}

    # ------------------------------------------------------------------
    # §11.7 [17]: 剧情承诺库合并
    # ------------------------------------------------------------------

    async def _merge_plot_promises(
        self,
        db: AsyncSession,
        project_id: int,
        updates: List[Dict],
        chapter_number: int = 0,
    ) -> Dict[str, int]:
        """合并剧情承诺库变更。

        实现 §11.7 [17]：
        - create → active + 埋设章节
        - advance → advancing + 推进日志
        - redeem → 已回收
        - cancel → 废弃
        """
        created = 0
        advanced = 0
        redeemed = 0

        for update in updates:
            action = update.get("action", "")
            title = update.get("title", "")

            if action == "create":
                if not title:
                    continue
                await vault_dao.create_plot_promise(
                    db,
                    {
                        "project_id": project_id,
                        "title": title,
                        "description": title,
                        "type": self._map_promise_type(update.get("type", "悬念")),
                        "status": "active",
                        "urgency": 5,
                        "planted_chapter": chapter_number,
                        "advancement_log": [
                            {
                                "chapter": chapter_number,
                                "event": "created",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        ],
                    },
                )
                created += 1
                logger.info(f"Plot promise created: {title}")

            elif action == "advance":
                if not title:
                    continue
                try:
                    promises = await vault_dao.get_plot_promises(db, project_id)
                    target = None
                    for p in promises:
                        if p.title == title or (
                            p.description and title in p.description
                        ):
                            target = p
                            break
                    if target:
                        log = target.advancement_log or []
                        log.append(
                            {
                                "chapter": chapter_number,
                                "event": "advanced",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                        await vault_dao.update_plot_promise(
                            db,
                            target,
                            {
                                "status": "advancing",
                                "advancement_log": log,
                                "urgency": min(10, (target.urgency or 5) + 1),
                            },
                        )
                        advanced += 1
                        logger.info(f"Plot promise advanced: {title}")
                except Exception as e:
                    logger.warning(
                        f"Failed to advance plot promise '{title}': {e}"
                    )

            elif action == "redeem":
                if not title:
                    continue
                try:
                    promises = await vault_dao.get_plot_promises(db, project_id)
                    target = None
                    for p in promises:
                        if p.title == title or (
                            p.description and title in p.description
                        ):
                            target = p
                            break
                    if target:
                        log = target.advancement_log or []
                        log.append(
                            {
                                "chapter": chapter_number,
                                "event": "redeemed",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                        await vault_dao.update_plot_promise(
                            db,
                            target,
                            {
                                "status": "resolved",
                                "advancement_log": log,
                            },
                        )
                        redeemed += 1
                        logger.info(f"Plot promise redeemed: {title}")
                except Exception as e:
                    logger.warning(
                        f"Failed to redeem plot promise '{title}': {e}"
                    )

            elif action == "cancel":
                if not title:
                    continue
                try:
                    promises = await vault_dao.get_plot_promises(db, project_id)
                    target = None
                    for p in promises:
                        if p.title == title or (
                            p.description and title in p.description
                        ):
                            target = p
                            break
                    if target:
                        log = target.advancement_log or []
                        log.append(
                            {
                                "chapter": chapter_number,
                                "event": "abandoned",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                        await vault_dao.update_plot_promise(
                            db,
                            target,
                            {
                                "status": "abandoned",
                                "advancement_log": log,
                            },
                        )
                        logger.info(f"Plot promise cancelled/abandoned: {title}")
                except Exception as e:
                    logger.warning(
                        f"Failed to cancel plot promise '{title}': {e}"
                    )

        return {"created": created, "advanced": advanced, "redeemed": redeemed}

    @staticmethod
    def _map_promise_type(ptype: str) -> str:
        """将中文剧情承诺类型映射到数据库枚举值。"""
        mapping = {
            "人物弧光": "arc",
            "剧情转折": "subplot",
            "悬念": "mystery",
            "关系发展": "promise",
            "世界观秘密": "foreshadowing",
        }
        return mapping.get(ptype, "mystery")

    # ------------------------------------------------------------------
    # §11.7 [18]: 世界观库合并
    # ------------------------------------------------------------------

    async def _merge_world(
        self,
        db: AsyncSession,
        project_id: int,
        updates: List[Dict],
        chapter_number: int = 0,
    ) -> Dict[str, int]:
        """合并世界观库变更。

        实现 §11.7 [18]：
        - create → 新设定 + 分类
        - expand → 补充说明
        - clarify → 修正
        - connect → 关联
        """
        created = 0
        expanded = 0

        for update in updates:
            action = update.get("action", "")
            name = update.get("name", "")

            if not name:
                continue

            if action == "create":
                await vault_dao.create_world_entry(
                    db,
                    {
                        "project_id": project_id,
                        "name": name,
                        "description": update.get("content", ""),
                        "category": update.get("category", "other"),
                        "source_chapter": chapter_number,
                        "reference_chapters": [chapter_number] if chapter_number else [],
                    },
                )
                created += 1
                logger.info(f"World entry created: {name}")

            elif action in ("expand", "clarify"):
                # 查找已有条目
                try:
                    entries = await vault_dao.get_world_entries(db, project_id)
                    target = None
                    for e in entries:
                        if e.name == name:
                            target = e
                            break
                    if target:
                        refs = target.reference_chapters or []
                        if chapter_number and chapter_number not in refs:
                            refs.append(chapter_number)

                        update_fields: Dict[str, Any] = {
                            "reference_chapters": refs,
                        }
                        new_content = update.get("content", "")
                        if new_content:
                            update_fields["description"] = (
                                target.description
                                + "\n\n[更新] "
                                + new_content
                            )

                        await vault_dao.update_world_entry(
                            db, target, update_fields
                        )
                        expanded += 1
                        logger.info(f"World entry {action}: {name}")
                except Exception as e:
                    logger.warning(
                        f"Failed to {action} world entry '{name}': {e}"
                    )

            elif action == "connect":
                # 关联：在相关实体中记录
                content = update.get("content", "")
                if content:
                    try:
                        entries = await vault_dao.get_world_entries(db, project_id)
                        target = None
                        for e in entries:
                            if e.name == name:
                                target = e
                                break
                        if target:
                            related = target.related_entities or []
                            if content not in related:
                                related.append(content)
                            await vault_dao.update_world_entry(
                                db,
                                target,
                                {"related_entities": related},
                            )
                            expanded += 1
                            logger.info(
                                f"World entry connected: {name} <-> {content}"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to connect world entry '{name}': {e}"
                        )

        return {"created": created, "expanded": expanded}

    # ------------------------------------------------------------------
    # §11.7 [19]: 卡牌池充实
    # ------------------------------------------------------------------

    async def _enrich_card_pool(
        self,
        db: AsyncSession,
        project_id: int,
        entries: List[Dict],
        chapter_number: int = 0,
    ) -> Dict[str, int]:
        """充实卡牌池。

        实现 §11.7 [19]：
        - 按 type + rarity 加入
        - 3 章新鲜期（×1.5）
        - 相同 title 不重复
        """
        added = 0

        # 获取现有卡牌，用于去重
        try:
            existing_cards = await card_dao.get_active_cards(db, project_id, count=1000)
            existing_titles = {c.name for c in existing_cards}
        except Exception:
            existing_titles = set()

        for entry in entries:
            title = entry.get("title", "")
            if not title or title in existing_titles:
                continue

            rarity = entry.get("rarity", "common")
            rarity_weight = {"common": 1, "rare": 2, "epic": 3}.get(rarity, 1)

            try:
                card = CardPool(
                    project_id=project_id,
                    name=title,
                    description=entry.get("description", ""),
                    rarity=rarity,
                    direction_type="interesting",
                    direction_text=entry.get("description", title),
                    source_label="Phase4",
                    source_chapter=chapter_number,
                    freshness_chapter=chapter_number,
                    rarity_weight=rarity_weight,
                    type=entry.get("type", "剧情"),
                    is_active=True,
                    status="active",
                    tags=["phase4", entry.get("type", "剧情"), rarity],
                )
                db.add(card)
                existing_titles.add(title)
                added += 1
                logger.info(f"Card pool entry added: {title} (rarity={rarity})")
            except Exception as e:
                logger.warning(f"Failed to add card '{title}': {e}")

        logger.info(f"Card pool enriched: {added} new cards added")
        return {"added": added}

    # ------------------------------------------------------------------
    # §11.7 [18a]: 置信度评估（P1-4）
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_phase4_confidence(changes: Dict[str, Any]) -> Dict[str, Any]:
        """评估 Phase 4 合并结果的置信度等级。

        对每类变更中的每个条目计算 confidence_level（HIGH/MEDIUM/LOW/REJECT），
        并生成整体置信度评估。

        Returns:
            dict with:
              - level: 整体 ConfidenceLevel 名称
              - auto_applied: 是否自动入库
              - levels: 每类变更的置信度分布
              - items_requiring_review: 需要人工审核的条目
        """
        items_requiring_review: List[Dict[str, Any]] = []
        level_counts = {lvl.value: 0 for lvl in ConfidenceLevel}

        # 评估角色变更
        char_changes = changes.get("characters", {})
        for key in ("created", "updated", "status_changed"):
            for item in char_changes.get(key, []):
                confidence = item.get("confidence", 0.8)
                level = evaluate_confidence(confidence)
                item["confidence_level"] = level.value
                level_counts[level.value] = level_counts.get(level.value, 0) + 1
                if level == ConfidenceLevel.LOW:
                    items_requiring_review.append({
                        "type": f"character_{key}",
                        "name": item.get("name", ""),
                        "id": item.get("id", ""),
                        "confidence": confidence,
                        "confidence_level": level.value,
                    })

        # 评估时间线变更（使用默认置信度 0.7）
        timeline_changes = changes.get("timeline", {})
        added_count = timeline_changes.get("added", 0)
        if added_count > 0:
            level = evaluate_confidence(0.7)
            level_counts[level.value] = level_counts.get(level.value, 0) + added_count

        # 评估剧情承诺变更（使用默认置信度 0.8）
        promise_changes = changes.get("plot_promises", {})
        for key in ("created", "advanced", "redeemed"):
            count = promise_changes.get(key, 0)
            if count > 0:
                level = evaluate_confidence(0.8)
                level_counts[level.value] = level_counts.get(level.value, 0) + count

        # 评估世界观变更（使用默认置信度 0.7）
        world_changes = changes.get("world", {})
        for key in ("created", "expanded"):
            count = world_changes.get(key, 0)
            if count > 0:
                level = evaluate_confidence(0.7)
                level_counts[level.value] = level_counts.get(level.value, 0) + count

        # 卡牌变更（使用默认置信度 0.85）
        card_changes = changes.get("card_pool", {})
        card_added = card_changes.get("added", 0)
        if card_added > 0:
            level = evaluate_confidence(0.85)
            level_counts[level.value] = level_counts.get(level.value, 0) + card_added

        # 计算整体置信度：按条目数量加权平均
        total_items = sum(level_counts.values())
        if total_items == 0:
            overall_level = ConfidenceLevel.HIGH
        else:
            # 使用加权平均计算整体置信度
            # HIGH=1.0, MEDIUM=0.65, LOW=0.4, REJECT=0.15
            score_map = {
                "high": 1.0,
                "medium": 0.65,
                "low": 0.4,
                "reject": 0.15,
            }
            weighted_sum = sum(
                level_counts.get(lvl.value, 0) * score_map.get(lvl.value, 0.0)
                for lvl in ConfidenceLevel
            )
            avg_score = weighted_sum / total_items if total_items > 0 else 1.0
            overall_level = evaluate_confidence(avg_score)

        return {
            "level": overall_level.value,
            "auto_applied": should_auto_apply(overall_level),
            "levels": level_counts,
            "items_requiring_review": items_requiring_review,
            "total_items": total_items,
        }

    # ------------------------------------------------------------------
    # §11.7 [20]: 变更日志归档
    # ------------------------------------------------------------------

    async def _archive_changelog(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        version: str,
        chapter_number: int,
        changes: Dict[str, Any],
    ) -> None:
        """归档变更日志。

        实现 §11.7 [20]：
        记录 version/chapter/timestamp/changes/summary
        """
        from app.models.vault_changelog import VaultChangelog

        timestamp = datetime.now(timezone.utc)

        # 记录角色变更
        for char in changes.get("characters", {}).get("created", []):
            log = VaultChangelog(
                project_id=project_id,
                chapter_id=chapter_id,
                change_type="add",
                entity_type="character",
                entity_id=char.get("id"),
                change_reason=f"Phase 4 新增角色: {char.get('name', '')}",
                meta_data={
                    "version": version,
                    "chapter": chapter_number,
                    "timestamp": timestamp.isoformat(),
                },
            )
            db.add(log)

        for char in changes.get("characters", {}).get("updated", []):
            log = VaultChangelog(
                project_id=project_id,
                chapter_id=chapter_id,
                change_type="update",
                entity_type="character",
                entity_id=char.get("id"),
                change_reason=f"Phase 4 更新角色: {char.get('name', '')}",
                meta_data={
                    "version": version,
                    "chapter": chapter_number,
                    "timestamp": timestamp.isoformat(),
                    "changes": char.get("changes", []),
                },
            )
            db.add(log)

        for char in changes.get("characters", {}).get("status_changed", []):
            log = VaultChangelog(
                project_id=project_id,
                chapter_id=chapter_id,
                change_type="update",
                entity_type="character",
                entity_id=char.get("id"),
                field_name="status",
                old_value=char.get("from"),
                new_value=char.get("to"),
                change_reason=f"Phase 4 状态变更: {char.get('name', '')}: {char.get('from')} → {char.get('to')}",
                meta_data={
                    "version": version,
                    "chapter": chapter_number,
                    "timestamp": timestamp.isoformat(),
                },
            )
            db.add(log)

        # 记录时间线变更
        added_count = changes.get("timeline", {}).get("added", 0)
        if added_count > 0:
            log = VaultChangelog(
                project_id=project_id,
                chapter_id=chapter_id,
                change_type="add",
                entity_type="timeline",
                change_reason=f"Phase 4 新增 {added_count} 个时间线事件",
                meta_data={
                    "version": version,
                    "chapter": chapter_number,
                    "timestamp": timestamp.isoformat(),
                    "count": added_count,
                },
            )
            db.add(log)

        # 记录剧情承诺变更
        promise_counts = changes.get("plot_promises", {})
        for action, label in [("created", "新增"), ("advanced", "推进"), ("redeemed", "回收")]:
            count = promise_counts.get(action, 0)
            if count > 0:
                log = VaultChangelog(
                    project_id=project_id,
                    chapter_id=chapter_id,
                    change_type="add" if action == "created" else "update",
                    entity_type="plot_promise",
                    change_reason=f"Phase 4 {label} {count} 个剧情承诺",
                    meta_data={
                        "version": version,
                        "chapter": chapter_number,
                        "timestamp": timestamp.isoformat(),
                        "count": count,
                        "action": action,
                    },
                )
                db.add(log)

        # 记录世界观变更
        world_counts = changes.get("world", {})
        for action, label in [("created", "新增"), ("expanded", "扩展")]:
            count = world_counts.get(action, 0)
            if count > 0:
                log = VaultChangelog(
                    project_id=project_id,
                    chapter_id=chapter_id,
                    change_type="add" if action == "created" else "update",
                    entity_type="world",
                    change_reason=f"Phase 4 {label} {count} 个世界观条目",
                    meta_data={
                        "version": version,
                        "chapter": chapter_number,
                        "timestamp": timestamp.isoformat(),
                        "count": count,
                        "action": action,
                    },
                )
                db.add(log)

        # 记录卡牌池变更
        card_count = changes.get("card_pool", {}).get("added", 0)
        if card_count > 0:
            log = VaultChangelog(
                project_id=project_id,
                chapter_id=chapter_id,
                change_type="add",
                entity_type="card",
                change_reason=f"Phase 4 新增 {card_count} 张卡牌",
                meta_data={
                    "version": version,
                    "chapter": chapter_number,
                    "timestamp": timestamp.isoformat(),
                    "count": card_count,
                },
            )
            db.add(log)

        logger.info(
            f"Changelog archived: version={version}, "
            f"chapter={chapter_number}"
        )


# Singleton instance
phase4_service = Phase4Service()
