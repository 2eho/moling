"""墨灵 (Moling) — Add sub_plots and sub_plot_status_logs tables

Support for tracking narrative sub-plots (支线情节) within projects.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create sub_plots and sub_plot_status_logs tables."""
    # ── sub_plots ──────────────────────────────────────────────────────
    op.create_table(
        "sub_plots",
        sa.Column("id", sa.String(36), primary_key=True, comment="主键 UUID"),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="所属项目 ID",
        ),
        sa.Column("title", sa.String(200), nullable=False, comment="支线名称"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="active",
            comment="支线状态: active / resolved / abandoned",
        ),
        sa.Column(
            "created_chapter",
            sa.Integer,
            nullable=False,
            server_default="1",
            comment="创建于章节",
        ),
        sa.Column(
            "last_advancement_chapter",
            sa.Integer,
            nullable=False,
            server_default="1",
            comment="最近推进章节",
        ),
        sa.Column(
            "health_status",
            sa.String(20),
            nullable=False,
            server_default="green",
            comment="健康状态: green / yellow / red",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="更新时间",
        ),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false", comment="软删除标记"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间"),
    )

    # ── sub_plot_status_logs ───────────────────────────────────────────
    op.create_table(
        "sub_plot_status_logs",
        sa.Column("id", sa.String(36), primary_key=True, comment="主键 UUID"),
        sa.Column(
            "subplot_id",
            sa.String(36),
            sa.ForeignKey("sub_plots.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="所属支线 ID",
        ),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="所属项目 ID",
        ),
        sa.Column("chapter", sa.Integer, nullable=False, comment="发生章节"),
        sa.Column("event_type", sa.String(50), nullable=False, comment="事件类型: advance / resolve / abandon"),
        sa.Column("old_status", sa.String(20), nullable=False, comment="变更前状态"),
        sa.Column("new_status", sa.String(20), nullable=False, comment="变更后状态"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="更新时间",
        ),
    )


def downgrade() -> None:
    """Drop sub_plot_status_logs then sub_plots tables."""
    op.drop_table("sub_plot_status_logs")
    op.drop_table("sub_plots")
