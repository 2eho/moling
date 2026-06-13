"""
墨灵 (Moling) — 数据库种子脚本.

插入演示数据：用户、项目、章节、卡牌、四库等。
运行方式：
    cd C:\Users\Admin\Desktop\MolingProject\moling-server
    python seed.py
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models import Base
from app.models.user import User
from app.models.project import Project
from app.models.chapter import Chapter
from app.models.card_pool import CardPool
from app.models.vault_character import VaultCharacter
from app.models.vault_timeline import VaultTimeline
from app.models.vault_plot_promise import VaultPlotPromise
from app.models.vault_world import VaultWorld

# ---- 配置 ----
settings = get_settings()

# 使用同步引擎（种子脚本不需要异步）
if settings.DATABASE_URL.startswith("sqlite"):
    sync_url = settings.DATABASE_URL.replace(
        "sqlite+aiosqlite://", "sqlite:///", 1
    )
    engine = create_engine(sync_url, echo=True)
else:
    # PostgreSQL
    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    engine = create_engine(sync_url, echo=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ---- 主函数 ----
def seed_data():
    """插入演示数据。"""

    # 创建表（如果不存在）
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # ---- 1. 创建演示用户 ----
        print("\n[种子] 创建演示用户...")
        demo_user = User(
            email="demo@moling.com",
            username="demo_user",
            password_hash=User.hash_password("Demo1234!"),  # 使用正确的密码哈希方法
            is_active=True,
            is_superuser=False,
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
        print(f"  ✓ 用户已创建: {demo_user.email} (ID: {demo_user.id})")

        # ---- 2. 创建演示项目 ----
        print("\n[种子] 创建演示项目...")
        demo_project = Project(
            user_id=demo_user.id,
            title="星穹剑仙",
            author="墨灵用户",
            genre="玄幻",
            tags=["修仙", "升级", "穿越"],
            synopsis="少年叶星穿越到修仙世界，凭借神秘小塔，一路逆袭成为剑仙。",
            worldview="三元界：下界（凡人）、中界（修士）、上界（仙人）。修炼等级：炼气、筑基、金丹、元婴、化神、渡劫、大乘、飞升。",
            protagonist="叶星：穿越者，拥有神秘小塔，可加速修炼、存储物品。性格谨慎、果断。",
            supporting_chars="林清儿（女主）、老塔（器灵）、天剑宗师父",
            word_count=125600,
            chapter_count=0,  # 会在添加章节后更新
            target_words=1000000,
            frequency="daily",
            style="descriptive",
            status="ongoing",
            creation_mode="card_first",
            template_id=None,
        )
        db.add(demo_project)
        db.commit()
        db.refresh(demo_project)
        print(f"  ✓ 项目已创建: {demo_project.title} (ID: {demo_project.id})")

        # ---- 3. 创建演示章节 ----
        print("\n[种子] 创建演示章节...")
        chapters = [
            Chapter(
                project_id=demo_project.id,
                title="第一章 穿越",
                order=1,
                content="叶星醒来时，发现自己躺在一间破旧的茅屋中。\n\n\"这是...哪里？\"他挣扎着坐起身，脑海中涌入大量陌生记忆。\n\n原身也叫叶星，是天剑宗外门弟子，因得罪内门执事而被废去修为，逐出宗门。",
                word_count=1250,
                status="draft",
            ),
            Chapter(
                project_id=demo_project.id,
                title="第二章 神秘小塔",
                order=2,
                content="就在叶星绝望之际，他突然发现自己的识海中多了一座九层小塔。\n\n\"这是什么？\"叶星心念一动，意识进入小塔。\n\n塔内空间不大，约莫一丈见方，中央有一块玉碑，上面刻着四个古字：\"万象归元\"。",
                word_count=1580,
                status="draft",
            ),
            Chapter(
                project_id=demo_project.id,
                title="第三章 初次修炼",
                order=3,
                content="叶星按照小塔玉碑上的功法《万象归元诀》开始修炼。\n\n出乎意料，原本被废的丹田竟然重新开始积聚灵气！\n\n\"这...这怎么可能？\"叶星震惊不已。\n\n一小时后，他竟然突破了炼气一层！",
                word_count=1890,
                status="draft",
            ),
        ]
        db.add_all(chapters)
        db.commit()

        # 更新项目章节数
        demo_project.chapter_count = len(chapters)
        db.commit()

        print(f"  ✓ 章节已创建: {len(chapters)} 章")

        # ---- 4. 创建演示卡牌 ----
        print("\n[种子] 创建演示卡牌...")
        cards = [
            CardPool(
                project_id=demo_project.id,
                name="神秘老者",
                card_type="character",
                description="一位神秘老者出现在山林中，似乎知道叶星的秘密。",
                tags=["伏笔", "角色"],
                weight=0.8,
                is_retired=False,
            ),
            CardPool(
                project_id=demo_project.id,
                name="失传秘籍",
                card_type="item",
                description="叶星在小塔深处发现了一本失传的上古秘籍。",
                tags=["金手指", "功法"],
                weight=0.9,
                is_retired=False,
            ),
            CardPool(
                project_id=demo_project.id,
                name="宗门大比",
                card_type="event",
                description="天剑宗三年一度的宗门大比即将开始，叶星有机会重新证明自己。",
                tags=["剧情推进", "冲突"],
                weight=0.7,
                is_retired=False,
            ),
        ]
        db.add_all(cards)
        db.commit()
        print(f"  ✓ 卡牌已创建: {len(cards)} 张")

        # ---- 5. 创建四库数据（角色库）----
        print("\n[种子] 创建四库数据（角色库）...")
        characters = [
            VaultCharacter(
                project_id=demo_project.id,
                name="叶星",
                role="protagonist",
                description="穿越者，原为天剑宗外门弟子，现拥有神秘小塔。",
                traits=["谨慎", "果断", "坚韧"],
                relationships="林清儿（好友）、老塔（主仆）",
            ),
            VaultCharacter(
                project_id=demo_project.id,
                name="林清儿",
                role="love_interest",
                description="天剑宗内门弟子，天赋异禀，对叶星有好感。",
                traits=["善良", "聪慧", "执着"],
                relationships="叶星（好友）",
            ),
            VaultCharacter(
                project_id=demo_project.id,
                name="老塔",
                role="mentor",
                description="神秘小塔的器灵，身份成谜，似乎知道许多上古秘辛。",
                traits=["深不可测", "毒舌", "护短"],
                relationships="叶星（主仆）",
            ),
        ]
        db.add_all(characters)
        db.commit()
        print(f"  ✓ 角色已创建: {len(characters)} 个")

        # ---- 6. 创建四库数据（时间线）----
        print("\n[种子] 创建四库数据（时间线）...")
        timelines = [
            VaultTimeline(
                project_id=demo_project.id,
                event="叶星穿越",
                time_description="故事开始",
                importance=5,
                related_chapters="1",
            ),
            VaultTimeline(
                project_id=demo_project.id,
                event="发现小塔",
                time_description="穿越后第一天",
                importance=5,
                related_chapters="2",
            ),
            VaultTimeline(
                project_id=demo_project.id,
                event="重修成功",
                time_description="穿越后第七天",
                importance=4,
                related_chapters="3",
            ),
        ]
        db.add_all(timelines)
        db.commit()
        print(f"  ✓ 时间线事件已创建: {len(timelines)} 条")

        # ---- 7. 创建四库数据（伏笔）----
        print("\n[种子] 创建四库数据（伏笔）...")
        plot_promises = [
            VaultPlotPromise(
                project_id=demo_project.id,
                description="小塔的真实来历",
                status="planted",
                payback_chapter=None,
            ),
            VaultPlotPromise(
                project_id=demo_project.id,
                description="叶星被废修为的真相",
                status="planted",
                payback_chapter=None,
            ),
        ]
        db.add_all(plot_promises)
        db.commit()
        print(f"  ✓ 伏笔已创建: {len(plot_promises)} 条")

        # ---- 8. 创建四库数据（世界观）----
        print("\n[种子] 创建四库数据（世界观）...")
        worlds = [
            VaultWorld(
                project_id=demo_project.id,
                category="地理",
                name="三元界",
                description="分为下界、中界、上界三个位面，每个位面都有不同的修炼资源和法则。",
            ),
            VaultWorld(
                project_id=demo_project.id,
                category="修炼体系",
                name="修炼等级",
                description="炼气、筑基、金丹、元婴、化神、渡劫、大乘、飞升。每个大境界分前、中、后期。",
            ),
            VaultWorld(
                project_id=demo_project.id,
                category="势力",
                name="天剑宗",
                description="下界七大修仙宗门之一，擅长剑修，宗内竞争激烈。",
            ),
        ]
        db.add_all(worlds)
        db.commit()
        print(f"  ✓ 世界观条目已创建: {len(worlds)} 条")

        print("\n" + "="*60)
        print("✅ 种子数据插入成功！")
        print("="*60)
        print(f"\n演示账号：")
        print(f"  邮箱: demo@moling.com")
        print(f"  密码: Demo1234!")
        print(f"\n演示项目：")
        print(f"  名称: {demo_project.title}")
        print(f"  ID: {demo_project.id}")
        print(f"\n现在可以使用演示账号登录，测试所有功能！")

    except Exception as e:
        db.rollback()
        print(f"\n❌ 种子数据插入失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("="*60)
    print("墨灵 (Moling) — 数据库种子脚本")
    print("="*60)
    print(f"\n数据库: {settings.DATABASE_URL[:50]}...")
    print("\n开始插入演示数据...\n")
    seed_data()
