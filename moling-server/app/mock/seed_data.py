"""
墨灵 (Moling) — Seed Data Script.

Inserts initial development data:
- 1 test user (admin@moling.com / password123)
- 1 example novel project ("墨灵")
- 2 chapters
- Several card pool entries
- Vault entries (characters, timeline, world)
"""

from __future__ import annotations

import asyncio
import logging
import platform

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.dao import (
    card_dao,
    chapter_dao,
    generation_dao,
    project_dao,
    user_dao,
    vault_dao,
)

logger = logging.getLogger(__name__)

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_db_url() -> str:
    """返回适配当前平台的数据库 URL（Windows + SQLite 用 aiosqlite）。"""
    settings = get_settings()
    url = settings.DATABASE_URL
    if platform.system() == "Windows" and url.startswith("sqlite"):
        if "aiosqlite" not in url:
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


async def seed_database(drop_first: bool = False) -> None:
    """Insert seed data into the database.

    Args:
        drop_first: If True, truncate all tables before seeding.
    """
    engine = create_async_engine(_get_db_url(), echo=False)
    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with session_factory() as db:
        if drop_first:
            logger.warning("Dropping all existing data...")
            meta = __import__("app.models", fromlist=["Base"]).Base.metadata
            for table in reversed(meta.sorted_tables):
                await db.execute(table.delete())
            await db.commit()

        # ================================================================
        # 1. Test User
        # ================================================================
        existing = await user_dao.get_by_email(db, "admin@moling.com")
        if existing:
            logger.info("Seed user already exists, skipping.")
        else:
            user = await user_dao.create(
                db,
                {
                    "email": "admin@moling.com",
                    "username": "墨灵管理员",
                    "password_hash": _pwd_ctx.hash("password123"),
                    "avatar_url": None,
                    "status": "active",
                },
            )
            logger.info("Created seed user: id=%d email=admin@moling.com", user.id)

            # ================================================================
            # 2. Example Project
            # ================================================================
            project = await project_dao.create(
                db,
                {
                    "user_id": user.id,
                    "title": "墨灵",
                    "author": "佚名",
                    "genre": "玄幻",
                    "tags": ["修仙", "奇幻", "东方玄幻"],
                    "synopsis": (
                        "在一个灵气复苏的现代世界，少年林墨意外觉醒了"
                        "上古墨灵血脉，从此踏上了一条与众不同的修仙之路。"
                    ),
                    "worldview": "现代都市与修仙世界交织的平行世界，灵气于二十年前开始复苏。",
                    "protagonist": "林墨，18岁，高中生，性格坚毅但内心温柔，拥有墨灵血脉。",
                    "target_words": 500000,
                    "frequency": "daily",
                    "style": "轻松幽默",
                    "creation_mode": "from_scratch",
                    "status": "active",
                },
            )
            logger.info("Created seed project: id=%d title=墨灵", project.id)

            # ================================================================
            # 3. Chapters
            # ================================================================
            ch1 = await chapter_dao.create(
                db,
                {
                    "project_id": project.id,
                    "title": "序章：灵气复苏",
                    "chapter_number": 1,
                    "content": (
                        "二十年前的今天，一场席卷全球的灵气潮汐改变了整个世界。\n\n"
                        "林墨坐在教室的最后一排，百无聊赖地望着窗外。"
                        "他今年十八岁，和所有同龄人一样，"
                        "对这个世界的变化早已习以为常。\n\n"
                        '"听说今晚子时会有新一轮的灵气潮汐。"\n\n'
                        "同桌张浩神秘兮兮地凑过来，"
                        "压低声音说：\n"
                        '"我表哥说，每次潮汐都会有人觉醒异能。"\n\n'
                        "林墨笑了笑，没有接话。"
                        "他从不觉得自己会是那个幸运儿。"
                    ),
                    "status": "completed",
                    "word_count": 2150,
                },
            )

            ch2 = await chapter_dao.create(
                db,
                {
                    "project_id": project.id,
                    "title": "第一章：墨灵觉醒",
                    "chapter_number": 2,
                    "content": (
                        "夜幕降临，城市的霓虹灯在灵气薄雾中显得格外迷离。\n\n"
                        "林墨独自站在天台，感受着空气中越来越浓郁的灵气。"
                        "他不知道为什么，总觉得今晚会有事情发生。\n\n"
                        "子时将至，天地间的灵气开始剧烈涌动。"
                        "林墨感觉到体内的血液在沸腾，"
                        "一种古老而强大的力量正在苏醒……"
                    ),
                    "status": "completed",
                    "word_count": 1800,
                },
            )

            logger.info(
                "Created chapters: #1 (id=%d), #2 (id=%d)", ch1.id, ch2.id
            )

            # ================================================================
            # 4. Card Pool
            # ================================================================
            cards_data = [
                {
                    "project_id": project.id,
                    "name": "命运转折",
                    "description": "主角遇到一个改变命运的关键事件",
                    "rarity": "epic",
                    "direction_type": "plot",
                    "direction_text": "安排一个意外事件，让主角获得关键机缘或遭遇重大危机",
                    "status": "active",
                    "freshness_chapter": 1,
                },
                {
                    "project_id": project.id,
                    "name": "神秘导师",
                    "description": "一位神秘人物出现，引导主角成长",
                    "rarity": "rare",
                    "direction_type": "character",
                    "direction_text": "引入一个亦正亦邪的导师角色，为主角提供指导但隐藏着秘密动机",
                    "status": "active",
                    "freshness_chapter": 1,
                },
                {
                    "project_id": project.id,
                    "name": "暗流涌动",
                    "description": "平静表面下的阴谋开始浮出水面",
                    "rarity": "rare",
                    "direction_type": "plot",
                    "direction_text": "揭露一个隐藏的阴谋或组织，让主角发现自己卷入了一场更大的纷争",
                    "status": "active",
                    "freshness_chapter": 1,
                },
                {
                    "project_id": project.id,
                    "name": "秘境探索",
                    "description": "发现一个神秘的秘境或遗迹",
                    "rarity": "epic",
                    "direction_type": "worldview",
                    "direction_text": "设计一个独特的秘境场景，包含古老文明遗留下的考验与宝藏",
                    "status": "active",
                    "freshness_chapter": 1,
                },
                {
                    "project_id": project.id,
                    "name": "情感羁绊",
                    "description": "主角与重要角色之间的情感互动",
                    "rarity": "common",
                    "direction_type": "character",
                    "direction_text": "发展一段重要的情感关系，可以是友情、亲情或爱情",
                    "status": "active",
                    "freshness_chapter": 1,
                },
                {
                    "project_id": project.id,
                    "name": "冲突升级",
                    "description": "矛盾激化，不可调和的冲突爆发",
                    "rarity": "legendary",
                    "direction_type": "conflict",
                    "direction_text": "让潜伏已久的矛盾彻底爆发，主角被迫做出艰难选择",
                    "status": "active",
                    "freshness_chapter": 1,
                },
            ]

            for card_data in cards_data:
                card = await card_dao.create(db, card_data)
                logger.debug("Created card: %s (id=%d)", card.name, card.id)

            logger.info("Created %d cards in the card pool", len(cards_data))

            # ================================================================
            # 5. Vault — Characters
            # ================================================================
            chars_data = [
                {
                    "project_id": project.id,
                    "name": "林墨",
                    "role": "protagonist",
                    "traits": ["坚毅", "善良", "执着", "幽默"],
                    "description": "18岁高中生，墨灵血脉觉醒者",
                    "background": "普通家庭出身，父母都是普通人，在一次灵气潮汐中意外觉醒上古墨灵血脉",
                    "chapter_count": 2,
                },
                {
                    "project_id": project.id,
                    "name": "张浩",
                    "role": "ally",
                    "traits": ["开朗", "忠诚", "八卦"],
                    "description": "林墨的同桌好友",
                    "background": "林墨从小到大的好朋友，性格开朗活泼",
                    "chapter_count": 2,
                },
                {
                    "project_id": project.id,
                    "name": "神秘老者",
                    "role": "ally",
                    "traits": ["神秘", "睿智", "深不可测"],
                    "description": "出现在林墨梦中的神秘老者",
                    "background": "身份不明，似乎与上古墨灵一族有着千丝万缕的联系",
                    "chapter_count": 0,
                },
            ]

            for char_data in chars_data:
                char = await vault_dao.create_character(db, char_data)
                logger.debug("Created vault character: %s (id=%d)", char.name, char.id)

            logger.info("Created %d vault characters", len(chars_data))

            # ================================================================
            # 6. Vault — Timeline
            # ================================================================
            timeline_data = [
                {
                    "project_id": project.id,
                    "chapter_number": 1,
                    "event": "灵气潮汐降临",
                    "description": "新一轮全球灵气潮汐开始，天地灵气浓度达到二十年来最高点",
                    "is_key_event": True,
                    "impact": "大量普通人觉醒异能，世界格局开始变化",
                    "characters_involved": ["林墨"],
                },
                {
                    "project_id": project.id,
                    "chapter_number": 1,
                    "event": "林墨体内血脉异动",
                    "description": "林墨在灵气潮汐中感到体内血液沸腾，墨灵血脉开始觉醒",
                    "is_key_event": True,
                    "impact": "主角林墨获得特殊能力，踏上修仙之路",
                    "characters_involved": ["林墨"],
                },
            ]

            for tl_data in timeline_data:
                tl = await vault_dao.create_timeline_event(db, tl_data)
                logger.debug("Created timeline event: %s (id=%d)", tl.event, tl.id)

            logger.info("Created %d timeline events", len(timeline_data))

            # ================================================================
            # 7. Vault — World Entries
            # ================================================================
            world_data = [
                {
                    "project_id": project.id,
                    "term": "灵气复苏",
                    "description": (
                        "二十年前开始，全球范围内的灵气浓度持续上升，"
                        "导致动植物变异、人类异能觉醒、古老传承重现。"
                    ),
                    "category": "history",
                    "reference_chapters": [1],
                },
                {
                    "project_id": project.id,
                    "term": "墨灵血脉",
                    "description": (
                        "上古时代流传下来的特殊血脉，拥有者可以操控"
                        "墨水与文字的力量，将文字转化为现实。"
                    ),
                    "category": "magic",
                    "reference_chapters": [1, 2],
                },
            ]

            for w_data in world_data:
                w_entry = await vault_dao.create_world_entry(db, w_data)
                logger.debug("Created world entry: %s (id=%d)", w_entry.term, w_entry.id)

            logger.info("Created %d world entries", len(world_data))

        await db.commit()
        logger.info("Seed complete!")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_database(drop_first="--drop" in __import__("sys").argv))
