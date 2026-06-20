"""墨灵 (Moling) — Model-Migration Alignment

将数据库 schema 与当前 ORM 模型对齐。

操作清单：
- 表重命名 (4): draw_records→draw_history, vault_worlds→vault_world,
               vault_timelines→vault_timeline, card_pools→card_pool
- 新建表 (9): dynamic_layers, system_config, phase4_tasks, templates, plans,
              user_subscriptions, notifications, secrets, vault_changelog
- 新增字段: users(4), chapters(9), card_pool(17), draw_history(1),
            vault_characters(8), vault_timeline(6), vault_plot_promises(3)
- 删除字段: chapters.dynamic_layer, vault_world.change_type, vault_world.rules
- 字段重命名: vault_world.term→name
- 类型修正: users.id Integer→String(36), chapters.id Integer→String(36),
            projects.user_id Integer→String(36), generation_tasks.user_id Integer→String(36),
            card_pool.direction_text String(500)→Text,
            generation_tasks.chapter_id Integer→String(36),
            draw_history.user_id Integer→String(36), draw_history.chapter_id Integer→String(36)
- 新增字段: vault_world.constraint, vault_world.related_entities, vault_world.source_chapter

Revision ID: 0004
Revises: 0003
Create Date: 2025-01-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ================================================================
    # Phase 1: Table renames (before any column ops)
    # ================================================================
    op.rename_table("draw_records", "draw_history")
    op.rename_table("vault_worlds", "vault_world")
    op.rename_table("vault_timelines", "vault_timeline")
    op.rename_table("card_pools", "card_pool")

    # ================================================================
    # Phase 2: Add missing columns to existing tables
    # (no FK dependency changes)
    # ================================================================

    # --- users: 4 missing columns ---
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("settings", sa.JSON(), nullable=True))
    op.add_column("users", sa.Column("reset_token", sa.String(255), nullable=True))
    op.add_column(
        "users",
        sa.Column("reset_token_expires", sa.DateTime(timezone=True), nullable=True),
    )

    # --- chapters: 9 new columns, 1 removal ---
    op.add_column(
        "chapters",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("chapters", sa.Column("used_card_ids", sa.JSON(), nullable=True))
    op.add_column("chapters", sa.Column("generation_mode", sa.String(50), nullable=True))
    op.add_column("chapters", sa.Column("generation_prompt", sa.Text(), nullable=True))
    op.add_column("chapters", sa.Column("generation_weights", sa.JSON(), nullable=True))
    op.add_column("chapters", sa.Column("generation_result", sa.Text(), nullable=True))
    op.add_column("chapters", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column(
        "chapters",
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "chapters",
        sa.Column("generation_duration", sa.Integer(), nullable=True),
    )
    # Remove dynamic_layer from chapters (separated into DynamicLayer table)
    op.drop_column("chapters", "dynamic_layer")

    # --- draw_history: 1 missing column ---
    op.add_column(
        "draw_history",
        sa.Column("cards_drawn", sa.JSON(), nullable=True),
    )

    # --- vault_characters: 8 missing columns ---
    op.add_column(
        "vault_characters",
        sa.Column("location", sa.String(200), nullable=True),
    )
    op.add_column(
        "vault_characters",
        sa.Column("appearance", sa.Text(), nullable=True),
    )
    op.add_column(
        "vault_characters",
        sa.Column("personality", sa.Text(), nullable=True),
    )
    op.add_column(
        "vault_characters",
        sa.Column("knowledge", sa.JSON(), nullable=True),
    )
    op.add_column(
        "vault_characters",
        sa.Column("confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "vault_characters",
        sa.Column("chapter_hist", sa.JSON(), nullable=True),
    )
    op.add_column(
        "vault_characters",
        sa.Column("current_state", sa.Text(), nullable=True),
    )
    op.add_column(
        "vault_characters",
        sa.Column("motivation", sa.Text(), nullable=True),
    )

    # --- vault_timeline: 6 missing columns ---
    op.add_column(
        "vault_timeline",
        sa.Column("day", sa.Integer(), nullable=True),
    )
    op.add_column(
        "vault_timeline",
        sa.Column("title", sa.String(200), nullable=True),
    )
    op.add_column(
        "vault_timeline",
        sa.Column("precedes", sa.JSON(), nullable=True),
    )
    op.add_column(
        "vault_timeline",
        sa.Column("confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "vault_timeline",
        sa.Column("source_chapter", sa.Integer(), nullable=True),
    )
    op.add_column(
        "vault_timeline",
        sa.Column("importance", sa.String(20), nullable=True),
    )

    # --- vault_plot_promises: 3 missing columns ---
    op.add_column(
        "vault_plot_promises",
        sa.Column("title", sa.String(200), nullable=True),
    )
    op.add_column(
        "vault_plot_promises",
        sa.Column("redeem_window", sa.Integer(), nullable=True),
    )
    op.add_column(
        "vault_plot_promises",
        sa.Column("confidence", sa.Float(), nullable=True),
    )

    # --- card_pool: 17 missing columns ---
    op.add_column("card_pool", sa.Column("type", sa.String(50), nullable=True))
    op.add_column(
        "card_pool",
        sa.Column(
            "source_label",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'初始卡池'"),
        ),
    )
    op.add_column(
        "card_pool",
        sa.Column(
            "pick_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "card_pool",
        sa.Column("last_drawn_chapter", sa.Integer(), nullable=True),
    )
    op.add_column(
        "card_pool",
        sa.Column("source_chapter", sa.Integer(), nullable=True),
    )
    op.add_column("card_pool", sa.Column("tags", sa.JSON(), nullable=True))
    op.add_column(
        "card_pool",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "card_pool",
        sa.Column("retired_chapter", sa.Integer(), nullable=True),
    )
    op.add_column(
        "card_pool",
        sa.Column("rarity_weight", sa.Integer(), nullable=True),
    )
    op.add_column("card_pool", sa.Column("characters", sa.JSON(), nullable=True))
    op.add_column("card_pool", sa.Column("plot_promises", sa.JSON(), nullable=True))
    op.add_column(
        "card_pool",
        sa.Column("timeline_point", sa.String(500), nullable=True),
    )
    op.add_column("card_pool", sa.Column("world_rules", sa.JSON(), nullable=True))
    op.add_column(
        "card_pool",
        sa.Column("current_story_state", sa.Text(), nullable=True),
    )
    op.add_column("card_pool", sa.Column("unresolved_hooks", sa.JSON(), nullable=True))
    op.add_column(
        "card_pool",
        sa.Column("dynamic_conflict_score", sa.Float(), nullable=True),
    )

    # --- vault_world: rename, drop, add ---
    op.alter_column("vault_world", "term", new_column_name="name")
    op.drop_column("vault_world", "change_type")
    op.drop_column("vault_world", "rules")
    op.add_column(
        "vault_world",
        sa.Column("constraint", sa.Text(), nullable=True),
    )
    op.add_column(
        "vault_world",
        sa.Column("related_entities", sa.JSON(), nullable=True),
    )
    op.add_column(
        "vault_world",
        sa.Column("source_chapter", sa.Integer(), nullable=True),
    )

    # ================================================================
    # Phase 3: PK & FK type changes
    # users.id Integer → String(36) UUID
    # chapters.id Integer → String(36) UUID
    # Propagates to all FK columns
    # ================================================================

    # -- 3a. Drop all FKs that reference users.id or chapters.id --
    # These constraints were auto-named by PostgreSQL.
    # We use IF EXISTS to safely handle cases where names differ.

    # FKs → users.id
    op.execute(
        "ALTER TABLE projects "
        "DROP CONSTRAINT IF EXISTS projects_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE generation_tasks "
        "DROP CONSTRAINT IF EXISTS generation_tasks_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE draw_history "
        "DROP CONSTRAINT IF EXISTS draw_records_user_id_fkey"
    )

    # FKs → chapters.id
    op.execute(
        "ALTER TABLE generation_tasks "
        "DROP CONSTRAINT IF EXISTS generation_tasks_chapter_id_fkey"
    )
    op.execute(
        "ALTER TABLE draw_history "
        "DROP CONSTRAINT IF EXISTS draw_records_chapter_id_fkey"
    )

    # -- 3b. Alter FK column types to match new PK type --
    op.execute("ALTER TABLE projects ALTER COLUMN user_id TYPE VARCHAR(36)")
    op.execute(
        "ALTER TABLE generation_tasks ALTER COLUMN user_id TYPE VARCHAR(36)"
    )
    op.execute(
        "ALTER TABLE generation_tasks ALTER COLUMN chapter_id TYPE VARCHAR(36)"
    )
    op.execute("ALTER TABLE draw_history ALTER COLUMN user_id TYPE VARCHAR(36)")
    op.execute(
        "ALTER TABLE draw_history ALTER COLUMN chapter_id TYPE VARCHAR(36)"
    )

    # -- 3c. Alter PK column types --
    # PostgreSQL will cast Int → Text. For production data, UUIDs should
    # be generated separately, but for dev databases with test data this
    # ensures the column type matches the model.
    op.execute(
        "ALTER TABLE users ALTER COLUMN id TYPE VARCHAR(36) USING id::text"
    )
    op.execute(
        "ALTER TABLE chapters ALTER COLUMN id TYPE VARCHAR(36) USING id::text"
    )

    # -- 3d. Re-create FKs with correct types --
    op.create_foreign_key(
        None, "projects", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        None,
        "generation_tasks",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "generation_tasks",
        "chapters",
        ["chapter_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        None,
        "draw_history",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "draw_history",
        "chapters",
        ["chapter_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -- 3e. Fix card_pool.direction_text type --
    op.alter_column(
        "card_pool",
        "direction_text",
        type_=sa.Text(),
        existing_type=sa.String(500),
    )

    # ================================================================
    # Phase 4: Create missing tables
    # ================================================================

    # --- system_config ---
    op.create_table(
        "system_config",
        sa.Column("key", sa.String(128), nullable=False, comment="配置键名"),
        sa.Column("value", sa.Text(), nullable=False, comment="配置值（加密存储）"),
        sa.Column(
            "description", sa.String(256), nullable=True, comment="配置说明"
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=True,
            comment="更新时间",
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    # --- templates ---
    op.create_table(
        "templates",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
            nullable=False,
            comment="主键 UUID",
        ),
        sa.Column(
            "name", sa.String(200), nullable=False, comment="模板名称"
        ),
        sa.Column(
            "description", sa.Text(), nullable=False, comment="模板描述"
        ),
        sa.Column(
            "genre", sa.String(50), nullable=False, comment="适用题材"
        ),
        sa.Column(
            "structure", sa.JSON(), nullable=True, comment="模板结构 (JSON)"
        ),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="创建者用户 ID",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # --- plans ---
    op.create_table(
        "plans",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
            nullable=False,
            comment="主键 UUID",
        ),
        sa.Column(
            "name", sa.String(100), nullable=False, comment="套餐名称"
        ),
        sa.Column("price", sa.Float(), nullable=False, comment="价格"),
        sa.Column(
            "currency",
            sa.String(10),
            nullable=False,
            server_default=sa.text("'CNY'"),
            comment="货币单位",
        ),
        sa.Column(
            "interval",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'month'"),
            comment="计费周期: month / year",
        ),
        sa.Column(
            "features", sa.JSON(), nullable=False, comment="套餐功能列表"
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="是否上架",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # --- user_subscriptions ---
    op.create_table(
        "user_subscriptions",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
            nullable=False,
            comment="主键 UUID",
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="用户 ID",
        ),
        sa.Column(
            "plan_id",
            sa.String(36),
            sa.ForeignKey("plans.id", ondelete="CASCADE"),
            nullable=False,
            comment="方案 ID",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
            comment="状态: active / trialing / canceled / expired",
        ),
        sa.Column(
            "start_date",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="订阅开始时间",
        ),
        sa.Column(
            "end_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="订阅结束时间",
        ),
        sa.Column(
            "auto_renew",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="是否自动续费",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_user_subscriptions_user_id",
        "user_subscriptions",
        ["user_id"],
    )

    # --- notifications ---
    op.create_table(
        "notifications",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="接收通知的用户 ID",
        ),
        sa.Column(
            "type",
            sa.String(50),
            nullable=False,
            comment="通知类型: phase4_failed / phase4_stuck / health_alert / ...",
        ),
        sa.Column(
            "title", sa.String(200), nullable=False, comment="通知标题"
        ),
        sa.Column(
            "content", sa.Text(), nullable=True, comment="通知正文"
        ),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="是否已读",
        ),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
            comment="关联项目 ID（可选，UUID）",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_notifications_user_id", "notifications", ["user_id"]
    )

    # --- secrets ---
    op.create_table(
        "secrets",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
            nullable=False,
            comment="主键 UUID",
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="所属项目 ID",
        ),
        sa.Column(
            "description", sa.Text(), nullable=False, comment="秘密描述"
        ),
        sa.Column(
            "known_by", sa.JSON(), nullable=False, comment="已知晓该秘密的角色名列表"
        ),
        sa.Column(
            "unknown_to",
            sa.JSON(),
            nullable=False,
            comment="不知晓该秘密的角色名列表",
        ),
        sa.Column(
            "secrecy_level",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'hidden'"),
            comment="保密层级: hidden / partial / revealed",
        ),
        sa.Column(
            "created_chapter",
            sa.Integer(),
            nullable=True,
            comment="秘密创建时的章节号",
        ),
        sa.Column(
            "debt",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="叙事债务值",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_secrets_project_id", "secrets", ["project_id"])

    # --- phase4_tasks ---
    op.create_table(
        "phase4_tasks",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column(
            "nonce",
            sa.String(100),
            nullable=False,
            unique=True,
            index=True,
            comment="幂等性令牌 (格式: ch${chapter}_${timestamp})",
        ),
        sa.Column(
            "project_id",
            sa.String(36),
            nullable=False,
            index=True,
            comment="项目 ID",
        ),
        sa.Column(
            "chapter_id",
            sa.String(36),
            nullable=False,
            index=True,
            comment="章节 ID",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
            comment="任务状态: pending / running / done / failed",
        ),
        sa.Column(
            "state",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'idle'"),
            comment="状态机状态: idle/queued/locking/extracting/...",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="错误信息 (任务失败时)",
        ),
        sa.Column(
            "safety_check",
            sa.JSON(),
            nullable=True,
            comment="SourceText 内容安全验证结果",
        ),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="重试次数 (最多 5 次)",
        ),
        sa.Column(
            "retry_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="下次重试时间 (指数退避)",
        ),
        sa.Column(
            "last_error",
            sa.Text(),
            nullable=True,
            comment="最后一次错误信息",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="开始执行时间",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="完成时间",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_phase4_tasks_nonce", "phase4_tasks", ["nonce"], unique=True
    )
    op.create_index(
        "ix_phase4_tasks_project_id", "phase4_tasks", ["project_id"]
    )
    op.create_index(
        "ix_phase4_tasks_chapter_id", "phase4_tasks", ["chapter_id"]
    )

    # --- dynamic_layers ---
    op.create_table(
        "dynamic_layers",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
            nullable=False,
            comment="主键 UUID",
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="所属项目 ID",
        ),
        sa.Column(
            "chapter_id",
            sa.String(36),
            sa.ForeignKey("chapters.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="所属章节 ID",
        ),
        sa.Column(
            "summary", sa.Text(), nullable=True, comment="前情摘要"
        ),
        sa.Column(
            "anchor_pov",
            sa.String(100),
            nullable=True,
            comment="POV - 视点角色",
        ),
        sa.Column(
            "anchor_location",
            sa.String(200),
            nullable=True,
            comment="地点 - 场景位置",
        ),
        sa.Column(
            "anchor_time",
            sa.String(100),
            nullable=True,
            comment="时间 - 场景时间",
        ),
        sa.Column(
            "must_hold", sa.JSON(), nullable=True, comment="必须保持的约束列表"
        ),
        sa.Column(
            "must_not", sa.JSON(), nullable=True, comment="必须避免的约束列表"
        ),
        sa.Column(
            "unresolved_hooks",
            sa.JSON(),
            nullable=True,
            comment="未解决的悬念列表",
        ),
        sa.Column(
            "recent_changes",
            sa.JSON(),
            nullable=True,
            comment="最近3章的变更日志",
        ),
        sa.Column(
            "information_asymmetry",
            sa.JSON(),
            nullable=True,
            comment="秘密矩阵 - 谁知道什么/谁还不知道",
        ),
        sa.Column(
            "feasibility_score",
            sa.Float(),
            nullable=True,
            comment="可行性评分 (0-1)",
        ),
        sa.Column(
            "health_check",
            sa.JSON(),
            nullable=True,
            comment="健康检查结果 (R1/R2/R3 告警)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # --- vault_changelog ---
    op.create_table(
        "vault_changelog",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
            nullable=False,
            comment="主键 UUID",
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="所属项目 ID",
        ),
        sa.Column(
            "chapter_id",
            sa.String(36),
            sa.ForeignKey("chapters.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="关联章节 ID",
        ),
        sa.Column(
            "change_type",
            sa.String(50),
            nullable=False,
            comment="变更类型: add / update / delete / archive",
        ),
        sa.Column(
            "entity_type",
            sa.String(50),
            nullable=False,
            comment="实体类型: character / timeline / plot_promise / world / secret",
        ),
        sa.Column(
            "entity_id",
            sa.String(36),
            nullable=True,
            comment="实体 ID (UUID)",
        ),
        sa.Column(
            "field_name",
            sa.String(100),
            nullable=True,
            comment="变更的字段名",
        ),
        sa.Column(
            "old_value", sa.Text(), nullable=True, comment="旧值"
        ),
        sa.Column(
            "new_value", sa.Text(), nullable=True, comment="新值"
        ),
        sa.Column(
            "change_reason",
            sa.Text(),
            nullable=True,
            comment="变更原因 (LLM 提取的变更说明)",
        ),
        sa.Column(
            "meta_data", sa.JSON(), nullable=True, comment="额外元数据"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Reverse the alignment migration — restore 0003 schema state."""
    # -- Drop new tables in reverse dependency order --
    op.drop_table("vault_changelog")
    op.drop_table("dynamic_layers")
    op.drop_table("phase4_tasks")
    op.drop_table("secrets")
    op.drop_table("notifications")
    op.drop_table("user_subscriptions")
    op.drop_table("plans")
    op.drop_table("templates")
    op.drop_table("system_config")

    # -- Reverse card_pool.direction_text type --
    op.alter_column(
        "card_pool",
        "direction_text",
        type_=sa.String(500),
        existing_type=sa.Text(),
    )

    # -- Reverse PK/FK type changes --
    op.execute(
        "ALTER TABLE draw_history "
        "DROP CONSTRAINT IF EXISTS draw_history_chapters_id_fkey"
    )
    op.execute(
        "ALTER TABLE draw_history "
        "DROP CONSTRAINT IF EXISTS draw_history_users_id_fkey"
    )
    op.execute(
        "ALTER TABLE generation_tasks "
        "DROP CONSTRAINT IF EXISTS generation_tasks_chapters_id_fkey"
    )
    op.execute(
        "ALTER TABLE generation_tasks "
        "DROP CONSTRAINT IF EXISTS generation_tasks_users_id_fkey"
    )
    op.execute(
        "ALTER TABLE projects "
        "DROP CONSTRAINT IF EXISTS projects_users_id_fkey"
    )

    op.execute(
        "ALTER TABLE chapters ALTER COLUMN id TYPE INTEGER USING id::integer"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN id TYPE INTEGER USING id::integer"
    )

    op.execute(
        "ALTER TABLE draw_history ALTER COLUMN chapter_id TYPE INTEGER"
    )
    op.execute(
        "ALTER TABLE draw_history ALTER COLUMN user_id TYPE INTEGER"
    )
    op.execute(
        "ALTER TABLE generation_tasks ALTER COLUMN chapter_id TYPE INTEGER"
    )
    op.execute(
        "ALTER TABLE generation_tasks ALTER COLUMN user_id TYPE INTEGER"
    )
    op.execute(
        "ALTER TABLE projects ALTER COLUMN user_id TYPE INTEGER"
    )

    op.create_foreign_key(
        None, "projects", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        None,
        "generation_tasks",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "generation_tasks",
        "chapters",
        ["chapter_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        None,
        "draw_history",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        None,
        "draw_history",
        "chapters",
        ["chapter_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -- Reverse vault_world columns --
    op.drop_column("vault_world", "source_chapter")
    op.drop_column("vault_world", "related_entities")
    op.drop_column("vault_world", "constraint")
    op.add_column(
        "vault_world",
        sa.Column("rules", sa.JSON(), nullable=True),
    )
    op.add_column(
        "vault_world",
        sa.Column("change_type", sa.String(20), nullable=True),
    )
    op.alter_column("vault_world", "name", new_column_name="term")

    # -- Reverse card_pool columns --
    op.drop_column("card_pool", "dynamic_conflict_score")
    op.drop_column("card_pool", "unresolved_hooks")
    op.drop_column("card_pool", "current_story_state")
    op.drop_column("card_pool", "world_rules")
    op.drop_column("card_pool", "timeline_point")
    op.drop_column("card_pool", "plot_promises")
    op.drop_column("card_pool", "characters")
    op.drop_column("card_pool", "rarity_weight")
    op.drop_column("card_pool", "retired_chapter")
    op.drop_column("card_pool", "is_active")
    op.drop_column("card_pool", "tags")
    op.drop_column("card_pool", "source_chapter")
    op.drop_column("card_pool", "last_drawn_chapter")
    op.drop_column("card_pool", "pick_count")
    op.drop_column("card_pool", "source_label")
    op.drop_column("card_pool", "type")

    # -- Reverse vault_plot_promises columns --
    op.drop_column("vault_plot_promises", "confidence")
    op.drop_column("vault_plot_promises", "redeem_window")
    op.drop_column("vault_plot_promises", "title")

    # -- Reverse vault_timeline columns --
    op.drop_column("vault_timeline", "importance")
    op.drop_column("vault_timeline", "source_chapter")
    op.drop_column("vault_timeline", "confidence")
    op.drop_column("vault_timeline", "precedes")
    op.drop_column("vault_timeline", "title")
    op.drop_column("vault_timeline", "day")

    # -- Reverse vault_characters columns --
    op.drop_column("vault_characters", "motivation")
    op.drop_column("vault_characters", "current_state")
    op.drop_column("vault_characters", "chapter_hist")
    op.drop_column("vault_characters", "confidence")
    op.drop_column("vault_characters", "knowledge")
    op.drop_column("vault_characters", "personality")
    op.drop_column("vault_characters", "appearance")
    op.drop_column("vault_characters", "location")

    # -- Reverse draw_history column --
    op.drop_column("draw_history", "cards_drawn")

    # -- Reverse chapters columns --
    op.add_column(
        "chapters",
        sa.Column("dynamic_layer", sa.JSON(), nullable=True),
    )
    op.drop_column("chapters", "generation_duration")
    op.drop_column("chapters", "retry_count")
    op.drop_column("chapters", "error_message")
    op.drop_column("chapters", "generation_result")
    op.drop_column("chapters", "generation_weights")
    op.drop_column("chapters", "generation_prompt")
    op.drop_column("chapters", "generation_mode")
    op.drop_column("chapters", "used_card_ids")
    op.drop_column("chapters", "confirmed_at")

    # -- Reverse users columns --
    op.drop_column("users", "reset_token_expires")
    op.drop_column("users", "reset_token")
    op.drop_column("users", "settings")
    op.drop_column("users", "bio")

    # -- Reverse table renames --
    op.rename_table("card_pool", "card_pools")
    op.rename_table("vault_timeline", "vault_timelines")
    op.rename_table("vault_world", "vault_worlds")
    op.rename_table("draw_history", "draw_records")
