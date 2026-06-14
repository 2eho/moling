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
from sqlalchemy import select, update

from app.config import get_settings
from app.dao import chapter_dao, project_dao, vault_dao, card_dao, generation_dao
from app.errors import ErrorCode, NotFoundError, ValidationError, AppError
from app.models import Chapter, Project, DynamicLayer, VaultCharacter, VaultTimeline, VaultPlotPromise, VaultWorld, CardPool, GenerationTask
from app.llm.client import llm_client

logger = logging.getLogger(__name__)
settings = get_settings()


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

        # 4. 创建或获取收纳任务记录
        # TODO: 这里应该创建一个 Phase4Task 记录，目前先用 GenerationTask 代替
        task = await generation_dao.get_by_chapter_and_type(
            db, chapter_id, "phase4"
        )
        if task is None:
            from uuid import uuid4
            task = GenerationTask(
                id=str(uuid4()),
                project_id=project_id,
                chapter_id=chapter_id,
                user_id=user_id,
                task_type="phase4",
                status="pending",
                input_params={"nonce": nonce},
                progress_percent=0,
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

    async def execute_storage(
        self,
        db: AsyncSession,
        task_id: str,
    ) -> Dict[str, Any]:
        """执行收纳流程（异步任务调用）。
        
        Args:
            db: 数据库会话
            task_id: 任务 ID
            
        Returns:
            收纳结果
        """
        # 1. 获取任务
        task = await generation_dao.get_by_id(db, task_id)
        if task is None:
            raise NotFoundError(
                error_code=ErrorCode.TASK_NOT_FOUND,
                detail="Task not found",
            )

        # 2. 更新任务状态为 running
        task.status = "running"
        task.progress_percent = 10
        task.progress_stage = "analyzing"
        await db.commit()

        try:
            # 3. 获取章节和项目信息
            chapter = await chapter_dao.get(db, task.chapter_id)
            project = await project_dao.get(db, chapter.project_id)
            
            # 4. 调用 LLM 分析章节内容，提取变更
            logger.info(f"Analyzing chapter {chapter.id} content with LLM")
            analysis_result = await self._analyze_chapter_content(
                db, project, chapter
            )
            
            task.progress_percent = 30
            await db.commit()

            # 5. 更新动态层（DynamicLayer）
            logger.info(f"Updating dynamic layer for chapter {chapter.id}")
            await self._update_dynamic_layer(
                db, project.id, chapter.id, analysis_result
            )
            
            task.progress_percent = 50
            await db.commit()

            # 6. 更新四库（Vault）实体
            logger.info(f"Updating vault entities for project {project.id}")
            await self._update_vault_entities(
                db, project.id, chapter.id, analysis_result
            )
            
            task.progress_percent = 70
            await db.commit()

            # 7. 更新卡牌池（CardPool）权重
            logger.info(f"Updating card pool weights for project {project.id}")
            await self._update_card_pool(
                db, project.id, chapter.id, analysis_result
            )
            
            task.progress_percent = 90
            await db.commit()

            # 8. 记录收纳历史（更新章节的 phase4_status）
            chapter.phase4_status = "done"
            task.status = "done"
            task.progress_percent = 100
            task.output_data = {
                "status": "success",
                "message": "收纳完成",
                "analysis": analysis_result,
            }
            await db.commit()

            logger.info(f"Phase 4 storage completed for chapter {chapter.id}")
            return task.output_data

        except Exception as e:
            logger.error(f"Phase 4 storage failed: {e}", exc_info=True)
            task.status = "failed"
            task.error_message = str(e)
            chapter = await chapter_dao.get(db, task.chapter_id)
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
        stmt = select(DynamicLayer).where(
            DynamicLayer.project_id == project_id,
            DynamicLayer.chapter_id == chapter_id,
        )
        result = await db.execute(stmt)
        dynamic_layer = result.scalar_one_or_none()
        
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
        
        # 更新未收束钩子（从分析中提取）
        # TODO: 从分析中提取未解决的悬念
        
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
                db, project_id, promise_data
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
        stmt = select(VaultCharacter).where(
            VaultCharacter.project_id == project_id,
            VaultCharacter.name == char_data["name"],
        )
        result = await db.execute(stmt)
        character = result.scalar_one_or_none()
        
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
    ) -> None:
        """更新或创建伏笔。"""
        # 查找是否已存在相似伏笔
        # TODO: 使用更复杂的匹配逻辑
        stmt = select(VaultPlotPromise).where(
            VaultPlotPromise.project_id == project_id,
            VaultPlotPromise.description.contains(promise_data["description"][:50]),
        )
        result = await db.execute(stmt)
        promise = result.scalar_one_or_none()
        
        if promise is None:
            # 创建新伏笔
            promise = VaultPlotPromise(
                project_id=project_id,
                description=promise_data["description"],
                type=promise_data.get("type", "mystery"),
                status=promise_data.get("status", "dormant"),
                urgency=promise_data.get("urgency", 5),
                related_characters=promise_data.get("related_characters", []),
                planted_chapter=0,  # TODO: 获取当前章节编号
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
        stmt = select(VaultWorld).where(
            VaultWorld.project_id == project_id,
            VaultWorld.term == world_data["term"],
        )
        result = await db.execute(stmt)
        world = result.scalar_one_or_none()
        
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
        # TODO: 从 generation task 中获取使用的卡牌 ID
        
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
        task_id: str,
    ) -> Dict[str, Any]:
        """查询收纳任务状态。"""
        task = await generation_dao.get_by_id(db, task_id)
        if task is None:
            raise NotFoundError(
                error_code=ErrorCode.TASK_NOT_FOUND,
                detail="Task not found",
            )
        
        # 验证权限
        if task.user_id != user_id:
            raise AppError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this task",
            )
        
        return {
            "task_id": task.id,
            "status": task.status,
            "progress_stage": task.progress_stage,
            "progress_percent": task.progress_percent,
            "error_message": task.error_message,
            "output_data": task.output_data,
        }


# Singleton instance
phase4_service = Phase4Service()
