"""墨灵 (Moling) — Initial Schema Migration.

Creates all 15 tables for the project:
- users, projects, chapters, generation_tasks
- card_pools, draw_records
- vault_characters, vault_timelines, vault_plot_promises, vault_worlds
- health_alerts

Also enables the pgvector extension for embedding columns.

Revision ID: 0001
Revises: None
Create Date: 2025-01-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- Enable pgvector extension ----
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # ---- 1. users ----
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False, comment="登录邮箱"),
        sa.Column("username", sa.String(50), nullable=False, comment="用户昵称"),
        sa.Column("password_hash", sa.String(255), nullable=False, comment="bcrypt 哈希后的密码"),
        sa.Column("avatar_url", sa.String(500), nullable=True, comment="头像 URL"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", comment="用户状态: active / disabled"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # ---- 2. projects ----
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="所属用户 ID"),
        sa.Column("title", sa.String(200), nullable=False, comment="作品标题"),
        sa.Column("author", sa.String(100), nullable=False, comment="作者署名"),
        sa.Column("genre", sa.String(50), nullable=False, comment="作品类型/题材"),
        sa.Column("tags", sa.JSON(), nullable=True, comment="标签数组"),
        sa.Column("synopsis", sa.Text(), nullable=True, comment="作品简介"),
        sa.Column("worldview", sa.Text(), nullable=True, comment="世界观设定"),
        sa.Column("protagonist", sa.String(100), nullable=True, comment="主角简介"),
        sa.Column("supporting_chars", sa.JSON(), nullable=True, comment="配角列表 (JSON)"),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0", comment="当前总字数"),
        sa.Column("target_words", sa.Integer(), nullable=True, comment="目标总字数"),
        sa.Column("frequency", sa.String(20), nullable=True, comment="更新频率: daily / weekly / custom"),
        sa.Column("style", sa.String(50), nullable=True, comment="写作风格"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft", comment="项目状态: draft / active / completed / archived"),
        sa.Column("creation_mode", sa.String(20), nullable=False, server_default="from_scratch", comment="创建模式: from_scratch / from_template"),
        sa.Column("template_id", sa.Integer(), nullable=True, comment="使用的模板 ID (预留)"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"])
    op.create_index("ix_projects_status", "projects", ["status"])

    # ---- 3. chapters ----
    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, comment="所属项目 ID"),
        sa.Column("title", sa.String(200), nullable=False, comment="章节标题"),
        sa.Column("content", sa.Text(), nullable=True, comment="章节正文内容"),
        sa.Column("chapter_number", sa.Integer(), nullable=False, comment="章节序号 (从 1 开始)"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft", comment="章节状态: draft / generating / completed / revised"),
        sa.Column("phase4_status", sa.String(20), nullable=False, server_default="none", comment="四阶段精修状态: none / pending / running / done / failed"),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0", comment="本章字数"),
        sa.Column("dynamic_layer", sa.JSON(), nullable=True, comment="动态层数据 (个性化要素嵌入)"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_chapters_project_id", "chapters", ["project_id"])
    op.create_index("ix_chapters_project_chapter", "chapters", ["project_id", "chapter_number"], unique=True)

    # ---- 4. generation_tasks ----
    op.create_table(
        "generation_tasks",
        sa.Column("id", sa.Uuid(), nullable=False, comment="任务唯一标识 (UUID)"),
        sa.Column("project_id", sa.Integer(), nullable=False, comment="所属项目 ID"),
        sa.Column("chapter_id", sa.Integer(), nullable=True, comment="关联章节 ID (可为空)"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="发起任务用户 ID"),
        sa.Column("task_type", sa.String(30), nullable=False, comment="任务类型: generate / phase4 / revise / analyze"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", comment="任务状态: pending / running / done / failed / cancelled"),
        sa.Column("input_params", sa.JSON(), nullable=False, comment="输入参数 (JSON)"),
        sa.Column("output_data", sa.JSON(), nullable=True, comment="输出数据 (JSON, 任务完成时填充)"),
        sa.Column("progress_stage", sa.String(100), nullable=True, comment="当前进度阶段描述"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0", comment="进度百分比 0-100"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息 (任务失败时)"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_generation_tasks_project_id", "generation_tasks", ["project_id"])
    op.create_index("ix_generation_tasks_chapter_id", "generation_tasks", ["chapter_id"])
    op.create_index("ix_generation_tasks_user_id", "generation_tasks", ["user_id"])
    op.create_index("ix_generation_tasks_status", "generation_tasks", ["status"])

    # ---- 5. card_pools ----
    op.create_table(
        "card_pools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, comment="所属项目 ID"),
        sa.Column("name", sa.String(200), nullable=False, comment="卡片名称"),
        sa.Column("description", sa.Text(), nullable=False, comment="卡片描述"),
        sa.Column("rarity", sa.String(20), nullable=False, comment="稀有度: common / rare / epic / legendary"),
        sa.Column("direction_type", sa.String(30), nullable=False, comment="方向类型: plot / character / worldview / style / conflict"),
        sa.Column("direction_text", sa.String(500), nullable=False, comment="方向指示文本"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", comment="状态: active / retired / archived"),
        sa.Column("freshness_chapter", sa.Integer(), nullable=True, comment="新鲜度章节号 (卡片创建时章节)"),
        sa.Column("draw_count", sa.Integer(), nullable=False, server_default="0", comment="被抽取次数"),
        sa.Column("remaining_lifetime", sa.Integer(), nullable=True, comment="剩余寿命 (章节数, 过期后失效)"),
        sa.Column("embedding", sa.Float(), nullable=True, comment="语义嵌入向量 (1536 维, pgvector)"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_card_pools_project_id", "card_pools", ["project_id"])
    op.create_index("ix_card_pools_rarity", "card_pools", ["rarity"])

    # ---- 6. draw_records ----
    op.create_table(
        "draw_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, comment="所属项目 ID"),
        sa.Column("chapter_id", sa.Integer(), nullable=True, comment="关联章节 ID (可为空)"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="抽卡用户 ID"),
        sa.Column("card_ids", sa.JSON(), nullable=False, comment="抽取的卡片 ID 列表"),
        sa.Column("weights", sa.JSON(), nullable=False, comment="各卡片的权重"),
        sa.Column("mode", sa.String(20), nullable=False, server_default="single", comment="抽取模式: none / single / dual / all / hybrid"),
        sa.Column("draw_round", sa.Integer(), nullable=False, server_default="0", comment="当前是第几轮抽卡 (1-based)"),
        sa.Column("remaining_redraws", sa.Integer(), nullable=False, server_default="0", comment="剩余重抽次数"),
        sa.Column("drawn_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="抽卡时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_draw_records_project_id", "draw_records", ["project_id"])
    op.create_index("ix_draw_records_user_id", "draw_records", ["user_id"])

    # ---- 7. vault_characters ----
    op.create_table(
        "vault_characters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, comment="所属项目 ID"),
        sa.Column("name", sa.String(100), nullable=False, comment="角色名称"),
        sa.Column("role", sa.String(30), nullable=False, comment="角色定位: protagonist / ally / neutral / opponent / antagonist"),
        sa.Column("faction", sa.String(100), nullable=True, comment="所属阵营/势力"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", comment="角色状态: active / inactive / deceased"),
        sa.Column("emotion", sa.String(50), nullable=True, comment="当前情绪状态"),
        sa.Column("traits", sa.JSON(), nullable=True, comment="性格特征数组"),
        sa.Column("description", sa.Text(), nullable=True, comment="角色描述"),
        sa.Column("background", sa.Text(), nullable=True, comment="角色背景故事"),
        sa.Column("relationships", sa.JSON(), nullable=True, comment="人际关系 (JSON 数组)"),
        sa.Column("state_machine", sa.JSON(), nullable=True, comment="状态机数据 (情感/状态转换)"),
        sa.Column("chapter_count", sa.Integer(), nullable=False, server_default="0", comment="已出场章节数"),
        sa.Column("embedding", sa.Float(), nullable=True, comment="语义嵌入向量 (pgvector)"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_vault_characters_project_id", "vault_characters", ["project_id"])

    # ---- 8. vault_timelines ----
    op.create_table(
        "vault_timelines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, comment="所属项目 ID"),
        sa.Column("chapter_number", sa.Integer(), nullable=False, comment="事件发生的章节号"),
        sa.Column("event", sa.String(300), nullable=False, comment="事件标题/摘要"),
        sa.Column("description", sa.Text(), nullable=False, comment="事件详细描述"),
        sa.Column("is_key_event", sa.Boolean(), nullable=False, server_default="false", comment="是否关键事件"),
        sa.Column("impact", sa.String(200), nullable=True, comment="事件影响描述"),
        sa.Column("characters_involved", sa.JSON(), nullable=True, comment="涉及角色名列表"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_vault_timelines_project_id", "vault_timelines", ["project_id"])
    op.create_index("ix_vault_timelines_chapter", "vault_timelines", ["project_id", "chapter_number"])

    # ---- 9. vault_plot_promises ----
    op.create_table(
        "vault_plot_promises",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, comment="所属项目 ID"),
        sa.Column("description", sa.Text(), nullable=False, comment="伏笔/承诺描述"),
        sa.Column("type", sa.String(30), nullable=False, comment="类型: foreshadowing / promise / mystery / setup"),
        sa.Column("status", sa.String(20), nullable=False, server_default="dormant", comment="状态: dormant / active / advancing / resolved / abandoned"),
        sa.Column("urgency", sa.Integer(), nullable=False, server_default="0", comment="紧迫度 0-10"),
        sa.Column("related_characters", sa.JSON(), nullable=True, comment="相关角色名列表"),
        sa.Column("planted_chapter", sa.Integer(), nullable=True, comment="埋下伏笔的章节号"),
        sa.Column("advancement_log", sa.JSON(), nullable=True, comment="推进日志 (事件列表)"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_vault_plot_promises_project_id", "vault_plot_promises", ["project_id"])

    # ---- 10. vault_worlds ----
    op.create_table(
        "vault_worlds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, comment="所属项目 ID"),
        sa.Column("term", sa.String(200), nullable=False, comment="术语/条目名称"),
        sa.Column("description", sa.Text(), nullable=False, comment="条目详细描述"),
        sa.Column("category", sa.String(50), nullable=False, comment="类别: geography / magic / technology / culture / history / rule / other"),
        sa.Column("change_type", sa.String(20), nullable=True, comment="变更类型: added / modified / removed (跟踪变化)"),
        sa.Column("rules", sa.JSON(), nullable=True, comment="该条目相关的规则列表"),
        sa.Column("reference_chapters", sa.JSON(), nullable=True, comment="引用章节号列表"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_vault_worlds_project_id", "vault_worlds", ["project_id"])

    # ---- 11. health_alerts ----
    op.create_table(
        "health_alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, comment="所属项目 ID"),
        sa.Column("rule", sa.String(100), nullable=False, comment="触发的规则名称"),
        sa.Column("title", sa.String(200), nullable=False, comment="告警标题"),
        sa.Column("detail", sa.Text(), nullable=False, comment="告警详细信息"),
        sa.Column("severity", sa.String(20), nullable=False, comment="严重程度: info / warning / critical"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", comment="是否活跃 (未解决)"),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True, comment="最后检查时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_health_alerts_project_id", "health_alerts", ["project_id"])
    op.create_index("ix_health_alerts_severity", "health_alerts", ["severity"])


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("health_alerts")
    op.drop_table("vault_worlds")
    op.drop_table("vault_plot_promises")
    op.drop_table("vault_timelines")
    op.drop_table("vault_characters")
    op.drop_table("draw_records")
    op.drop_table("card_pools")
    op.drop_table("generation_tasks")
    op.drop_table("chapters")
    op.drop_table("projects")
    op.drop_table("users")
