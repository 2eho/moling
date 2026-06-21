"""Moling - Vault Service.

Business logic for the Four Databases (四库): Characters, Timeline, Plot Promises, World Building.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import vault_dao, project_dao, chapter_dao
from app.errors import NotFoundError, ErrorCode
from app.utils.security import verify_project_ownership
from app.models import VaultTimeline, VaultPlotPromise
from app.schemas.vault import CharacterResp, TimelineResp, PlotPromiseResp, WorldResp


class VaultService:
    """Service for vault operations (four databases)."""

    # ============ Characters ============

    async def list_characters(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
    ) -> list[CharacterResp]:
        """List all characters in a project's vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        characters = await vault_dao.get_characters(db, project_id)
        return [CharacterResp.model_validate(c) for c in characters]

    async def create_character(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        character_data: dict[str, Any],
    ) -> CharacterResp:
        """Create a new character in the vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Create character
        character_data["project_id"] = project_id
        character = await vault_dao.create_character(db, character_data)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise
        await db.refresh(character)

        return CharacterResp.model_validate(character)

    async def update_character(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        character_id: int,
        character_data: dict[str, Any],
    ) -> CharacterResp:
        """Update a character in the vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Get character
        character = await vault_dao.get_character(db, character_id)
        if character is None or character.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.CHARACTER_NOT_FOUND,
                detail="Character not found",
            )

        # Update character
        character = await vault_dao.update_character(db, character, character_data)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise
        await db.refresh(character)

        return CharacterResp.model_validate(character)

    async def delete_character(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        character_id: int,
    ) -> None:
        """Delete a character from the vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Delete character
        await vault_dao.delete_character(db, character_id)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise

    async def get_character(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        character_id: int,
    ) -> CharacterResp:
        """Get a single character by ID."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Get character
        character = await vault_dao.get_character(db, character_id)
        if character is None or character.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.CHARACTER_NOT_FOUND,
                detail="Character not found",
            )

        return CharacterResp.model_validate(character)

    # ============ Timeline ============

    async def list_timeline(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
    ) -> list[TimelineResp]:
        """List all timeline events in a project's vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        events = await vault_dao.get_timeline(db, project_id)
        return [TimelineResp.model_validate(e) for e in events]

    async def create_timeline_event(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        event_data: dict,
    ) -> TimelineResp:
        """Create a new timeline event in the vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Create event
        event_data["project_id"] = project_id
        event = await vault_dao.create_timeline_event(db, event_data)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise
        await db.refresh(event)

        return TimelineResp.model_validate(event)

    async def get_timeline_event(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        event_id: int,
    ) -> TimelineResp:
        """Get a single timeline event by ID."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Get event
        event = await vault_dao.get_timeline_event(db, event_id)
        if event is None or event.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.TIMELINE_NOT_FOUND,
                detail="Timeline event not found",
            )

        return TimelineResp.model_validate(event)

    async def update_timeline_event(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        event_id: int,
        event_data: dict,
    ) -> TimelineResp:
        """Update a timeline event in the vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Get event
        event = await vault_dao.get_timeline_event(db, event_id)
        if event is None or event.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.TIMELINE_NOT_FOUND,
                detail="Timeline event not found",
            )

        # Update event
        event = await vault_dao.update_timeline_event(db, event, event_data)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise
        await db.refresh(event)

        return TimelineResp.model_validate(event)

    async def delete_timeline_event(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        event_id: int,
    ) -> None:
        """Delete a timeline event from the vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Delete event
        await vault_dao.delete_timeline_event(db, event_id)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise

    # ============ Plot Promises ============

    async def list_plot_promises(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
    ) -> list[PlotPromiseResp]:
        """List all plot promises in a project's vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        promises = await vault_dao.get_plot_promises(db, project_id)
        return [PlotPromiseResp.model_validate(p) for p in promises]

    async def create_plot_promise(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        promise_data: dict,
    ) -> PlotPromiseResp:
        """Create a new plot promise in the vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Create promise
        promise_data["project_id"] = project_id
        promise = await vault_dao.create_plot_promise(db, promise_data)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise
        await db.refresh(promise)

        return PlotPromiseResp.model_validate(promise)

    async def get_plot_promise(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        promise_id: int,
    ) -> PlotPromiseResp:
        """Get a single plot promise by ID."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Get promise
        promise = await vault_dao.get_plot_promise(db, promise_id)
        if promise is None or promise.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.PLOT_PROMISE_NOT_FOUND,
                detail="Plot promise not found",
            )

        return PlotPromiseResp.model_validate(promise)

    async def update_plot_promise(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        promise_id: int,
        promise_data: dict,
    ) -> PlotPromiseResp:
        """Update a plot promise in the vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Get promise
        promise = await vault_dao.get_plot_promise(db, promise_id)
        if promise is None or promise.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.PLOT_PROMISE_NOT_FOUND,
                detail="Plot promise not found",
            )

        # Update promise
        promise = await vault_dao.update_plot_promise(db, promise, promise_data)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise
        await db.refresh(promise)

        return PlotPromiseResp.model_validate(promise)

    async def delete_plot_promise(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        promise_id: int,
    ) -> None:
        """Delete a plot promise from the vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Delete promise
        await vault_dao.delete_plot_promise(db, promise_id)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise

    # ============ World Building ============

    async def list_world_entries(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
    ) -> list[WorldResp]:
        """List all world-building entries in a project's vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        entries = await vault_dao.get_world_entries(db, project_id)
        return [WorldResp.model_validate(e) for e in entries]

    async def create_world_entry(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        entry_data: dict,
    ) -> WorldResp:
        """Create a new world-building entry in the vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Create entry
        entry_data["project_id"] = project_id
        entry = await vault_dao.create_world_entry(db, entry_data)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise
        await db.refresh(entry)

        return WorldResp.model_validate(entry)

    async def get_world_entry(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        entry_id: int,
    ) -> WorldResp:
        """Get a single world-building entry by ID."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Get entry
        entry = await vault_dao.get_world_entry(db, entry_id)
        if entry is None or entry.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.WORLD_NOT_FOUND,
                detail="World entry not found",
            )

        return WorldResp.model_validate(entry)

    async def update_world_entry(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        entry_id: int,
        entry_data: dict,
    ) -> WorldResp:
        """Update a world-building entry in the vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Get entry
        entry = await vault_dao.get_world_entry(db, entry_id)
        if entry is None or entry.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.WORLD_NOT_FOUND,
                detail="World entry not found",
            )

        # Update entry
        entry = await vault_dao.update_world_entry(db, entry, entry_data)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise
        await db.refresh(entry)

        return WorldResp.model_validate(entry)

    async def delete_world_entry(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        entry_id: int,
    ) -> None:
        """Delete a world-building entry from the vault."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Delete entry
        await vault_dao.delete_world_entry(db, entry_id)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise

    async def update_from_chapter(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
    ) -> dict:
        """从章节提取实体并更新保险库条目。

        在 worker 任务中调用，db 由调用方通过 get_worker_session() 提供。

        Returns:
            dict with update results (counts of created/updated entries)
        """
        # 1. 验证项目和章节
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )

        chapter = await chapter_dao.get(db, chapter_id)
        if chapter is None:
            raise NotFoundError(
                error_code=ErrorCode.CHAPTER_NOT_FOUND,
                detail="Chapter not found",
            )

        content = chapter.content or ""
        if not content.strip():
            return {
                "project_id": project_id,
                "chapter_id": chapter_id,
                "created": 0,
                "updated": 0,
                "entities_found": 0,
                "message": "章节内容为空，跳过分析",
            }

        # 2. 简单的文本实体提取（基于中文命名模式）
        import re

        entities = {
            "characters": set(),
            "locations": set(),
            "items": set(),
        }

        # 提取中文姓名模式：2-4 个中文字符，在对话标记或动词附近
        # 匹配引号内或特殊标记后的连续中文字符
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 匹配中文姓名（2-4 个汉字，出现在对话标记前）
            name_matches = re.findall(
                r'([\u4e00-\u9fff]{2,4})[：:　]',
                line,
            )
            for name in name_matches:
                # 过滤掉常见非姓名词
                common_words = {"但是", "然而", "虽然", "因为", "所以",
                                "不过", "这个", "那个", "这些", "那些",
                                "我们", "你们", "他们", "它们", "她们",
                                "没有", "可以", "还是", "不是", "就是",
                                "什么", "怎么", "这样", "那样", "如果",
                                "已经", "一个", "还有", "之后", "时候",
                                "突然", "开始", "最后", "知道", "看到",
                                "自己", "只见", "只听"}
                if name not in common_words:
                    entities["characters"].add(name)

            # 提取含"在""到""去""从"等地点的上下文
            loc_keywords = re.findall(
                r'(?:在|到|去|从|进入|来到|前往|返回|离开)([\u4e00-\u9fff]{2,6})(?:[，。,\.!！]|$)',
                line,
            )
            for loc in loc_keywords:
                entities["locations"].add(loc)

            # 提取含"拿起""握着""背着"等物品的上下文
            item_matches = re.findall(
                r'(?:拿起|握着|背着|提着|拎着|戴上|穿着|手中|一把|一根|一个|一本|一卷)'
                r'([\u4e00-\u9fff]{2,4})(?:\s|，|。|！|？|\.|,|!|\?|$)',
                line,
            )
            for item in item_matches:
                entities["items"].add(item)

        # 3. 更新保险库条目
        created_count = 0
        updated_count = 0

        # 更新角色
        for char_name in entities["characters"]:
            existing = await vault_dao.get_character_by_name(
                db, project_id, char_name
            )

            if existing:
                existing.chapter_count = (existing.chapter_count or 0) + 1
                updated_count += 1
            else:
                new_char = await vault_dao.create_character(
                    db,
                    {
                        "project_id": project_id,
                        "name": char_name,
                        "role": "neutral",
                        "description": f"从第 {chapter.chapter_number} 章自动提取",
                        "traits": [],
                        "chapter_count": 1,
                    },
                )
                created_count += 1

        # 更新地点（作为世界观元素存储）
        for loc_name in entities["locations"]:
            existing = await vault_dao.get_world_entry_by_term(
                db, project_id, loc_name
            )

            if existing:
                updated_count += 1
            else:
                new_world = await vault_dao.create_world_entry(
                    db,
                    {
                        "project_id": project_id,
                        "name": loc_name,
                        "description": f"从第 {chapter.chapter_number} 章自动提取的地点",
                        "category": "location",
                        "reference_chapters": [],
                    },
                )
                created_count += 1

        # 更新物品（作为世界观元素存储）
        for item_name in entities["items"]:
            existing = await vault_dao.get_world_entry_by_term(
                db, project_id, item_name
            )

            if existing:
                updated_count += 1
            else:
                new_item = await vault_dao.create_world_entry(
                    db,
                    {
                        "project_id": project_id,
                        "name": item_name,
                        "description": f"从第 {chapter.chapter_number} 章自动提取的物品",
                        "category": "item",
                        "reference_chapters": [],
                    },
                )
                created_count += 1

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise

        return {
            "project_id": project_id,
            "chapter_id": chapter_id,
            "chapter_number": chapter.chapter_number,
            "created": created_count,
            "updated": updated_count,
            "entities_found": {
                "characters": len(entities["characters"]),
                "locations": len(entities["locations"]),
                "items": len(entities["items"]),
            },
            "total_entities": (
                len(entities["characters"])
                + len(entities["locations"])
                + len(entities["items"])
            ),
            "message": (
                f"从第 {chapter.chapter_number} 章提取并更新保险库："
                f"新增 {created_count} 条，更新 {updated_count} 条"
            ),
        }

    async def get_summary(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
    ) -> dict:
        """Get four databases summary (characters, timeline, plot promises, world)."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Count and get from vault DAO
        character_count = await vault_dao.count_characters(db, project_id)
        timeline_count = await vault_dao.count_timeline_events(db, project_id)
        promise_count = await vault_dao.count_plot_promises(db, project_id)
        world_count = await vault_dao.count_world_entries(db, project_id)

        # Get recent characters (take last 5 from full list)
        all_characters = await vault_dao.get_characters(db, project_id)
        recent_characters = sorted(
            all_characters, key=lambda c: c.updated_at or c.created_at, reverse=True
        )[:5]

        return {
            "success": True,
            "summary": {
                "character_count": character_count,
                "timeline_count": timeline_count,
                "promise_count": promise_count,
                "world_count": world_count,
            },
            "recent_characters": [
                CharacterResp.model_validate(c) for c in recent_characters
            ],
        }


# Singleton instance
vault_service = VaultService()
