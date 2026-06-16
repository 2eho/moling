#!/usr/bin/env python3
"""墨灵性能测试 — 测试数据生成脚本.

此脚本用于生成大量测试数据：
- 10,000 个项目
- 100,000 个章节
- 50,000 个卡牌

使用方法：
    python generate_test_data.py --projects 10000 --chapters 100000 --cards 50000
    python generate_test_data.py --all  # 生成所有测试数据
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.base import async_session
from app.models.project import Project
from app.models.chapter import Chapter
from app.models.card_pool import CardPool
from app.models.user import User
import asyncio
import random


class TestDataGenerator:
    """测试数据生成器."""

    def __init__(self, db_session):
        self.db = db_session
        self.user_id = None

    async def get_or_create_test_user(self):
        """获取或创建测试用户."""
        # 查询是否已存在测试用户
        result = await self.db.execute(
            User.__table__.select().where(User.email == "perf_test@moling.com")
        )
        user = result.first()
        
        if user:
            self.user_id = user.id
            return user
        
        # 创建测试用户
        new_user = User(
            email="perf_test@moling.com",
            nickname="性能测试用户",
            password_hash="hashed_password",  # 实际应用中需要正确哈希
        )
        self.db.add(new_user)
        await self.db.flush()
        self.user_id = new_user.id
        return new_user

    async def generate_projects(self, count=10000):
        """生成测试项目."""
        print(f"\n生成 {count} 个项目...")
        print("="*60)
        
        batch_size = 100
        start_time = time.time()
        
        for i in range(0, count, batch_size):
            batch = []
            for j in range(min(batch_size, count - i)):
                project = Project(
                    user_id=self.user_id,
                    title=f"性能测试项目_{i + j + 1}",
                    genre=random.choice(["fantasy", "sci_fi", "romance", "mystery", "horror"]),
                    language="zh",
                    status="active",
                )
                batch.append(project)
            
            self.db.add_all(batch)
            await self.db.flush()
            
            progress = min(i + batch_size, count)
            print(f"进度: {progress}/{count} ({progress/count*100:.1f}%)")
        
        await self.db.commit()
        
        elapsed = time.time() - start_time
        print(f"✅ 项目生成完成，耗时: {elapsed:.2f}s")
        return elapsed

    async def generate_chapters(self, project_count=10000, chapters_per_project=10):
        """生成测试章节."""
        total_chapters = project_count * chapters_per_project
        print(f"\n生成 {total_chapters} 个章节（{project_count} 个项目 × {chapters_per_project} 章节）...")
        print("="*60)
        
        # 获取所有项目 ID
        result = await self.db.execute(
            Project.__table__.select().where(Project.user_id == self.user_id)
        )
        projects = result.fetchall()
        
        if not projects:
            print("❌ 没有找到项目，请先生成项目")
            return 0
        
        batch_size = 100
        start_time = time.time()
        generated = 0
        
        for project in projects:
            project_id = project.id
            batch = []
            
            for chapter_order in range(1, chapters_per_project + 1):
                chapter = Chapter(
                    project_id=project_id,
                    title=f"章节 {chapter_order}",
                    content=f"这是第 {chapter_order} 章的内容。",
                    order=chapter_order,
                    word_count=random.randint(1000, 5000),
                )
                batch.append(chapter)
                generated += 1
                
                if len(batch) >= batch_size:
                    self.db.add_all(batch)
                    await self.db.flush()
                    batch = []
                
                if generated % 1000 == 0:
                    progress = generated / total_chapters * 100
                    print(f"进度: {generated}/{total_chapters} ({progress:.1f}%)")
            
            if batch:
                self.db.add_all(batch)
                await self.db.flush()
        
        await self.db.commit()
        
        elapsed = time.time() - start_time
        print(f"✅ 章节生成完成，耗时: {elapsed:.2f}s")
        return elapsed

    async def generate_cards(self, project_count=10000, cards_per_project=5):
        """生成测试卡牌."""
        total_cards = project_count * cards_per_project
        print(f"\n生成 {total_cards} 个卡牌（{project_count} 个项目 × {cards_per_project} 卡牌）...")
        print("="*60)
        
        # 获取所有项目 ID
        result = await self.db.execute(
            Project.__table__.select().where(Project.user_id == self.user_id)
        )
        projects = result.fetchall()
        
        if not projects:
            print("❌ 没有找到项目，请先生成项目")
            return 0
        
        batch_size = 100
        start_time = time.time()
        generated = 0
        
        for project in projects:
            project_id = project.id
            batch = []
            
            for card_index in range(cards_per_project):
                card = CardPool(
                    project_id=project_id,
                    name=f"卡牌 {card_index + 1}",
                    type=random.choice(["character", "item", "location", "event"]),
                    description=f"这是卡牌 {card_index + 1} 的描述。",
                )
                batch.append(card)
                generated += 1
                
                if len(batch) >= batch_size:
                    self.db.add_all(batch)
                    await self.db.flush()
                    batch = []
                
                if generated % 1000 == 0:
                    progress = generated / total_cards * 100
                    print(f"进度: {generated}/{total_cards} ({progress:.1f}%)")
            
            if batch:
                self.db.add_all(batch)
                await self.db.flush()
        
        await self.db.commit()
        
        elapsed = time.time() - start_time
        print(f"✅ 卡牌生成完成，耗时: {elapsed:.2f}s")
        return elapsed

    async def generate_all(self, projects=10000, chapters_per_project=10, cards_per_project=5):
        """生成所有测试数据."""
        print("="*60)
        print("墨灵性能测试 — 测试数据生成")
        print("="*60)
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"配置:")
        print(f"  - 项目数: {projects}")
        print(f"  - 每项目章节数: {chapters_per_project}")
        print(f"  - 每项目卡牌数: {cards_per_project}")
        print(f"  - 总章节数: {projects * chapters_per_project}")
        print(f"  - 总卡牌数: {projects * cards_per_project}")
        print("="*60)
        
        start_time = time.time()
        
        # 1. 获取或创建测试用户
        await self.get_or_create_test_user()
        print(f"✅ 测试用户已就绪 (ID: {self.user_id})")
        
        # 2. 生成项目
        projects_time = await self.generate_projects(projects)
        
        # 3. 生成章节
        chapters_time = await self.generate_chapters(projects, chapters_per_project)
        
        # 4. 生成卡牌
        cards_time = await self.generate_cards(projects, cards_per_project)
        
        total_time = time.time() - start_time
        
        print("\n" + "="*60)
        print("生成完成")
        print("="*60)
        print(f"总耗时: {total_time:.2f}s")
        print(f"  - 项目: {projects_time:.2f}s")
        print(f"  - 章节: {chapters_time:.2f}s")
        print(f"  - 卡牌: {cards_time:.2f}s")
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)


async def main():
    """主函数."""
    parser = argparse.ArgumentParser(description="墨灵性能测试 — 测试数据生成脚本")
    parser.add_argument("--projects", type=int, default=10000, help="项目数量（默认: 10000）")
    parser.add_argument("--chapters-per-project", type=int, default=10, help="每项目章节数（默认: 10）")
    parser.add_argument("--cards-per-project", type=int, default=5, help="每项目卡牌数（默认: 5）")
    parser.add_argument("--all", action="store_true", help="生成所有测试数据（使用默认配置）")
    args = parser.parse_args()
    
    # 创建数据库会话
    async with async_session() as db:
        generator = TestDataGenerator(db)
        
        if args.all:
            await generator.generate_all()
        else:
            await generator.generate_all(
                projects=args.projects,
                chapters_per_project=args.chapters_per_project,
                cards_per_project=args.cards_per_project,
            )


if __name__ == "__main__":
    asyncio.run(main())
