"""add ingest_jobs table

Revision ID: 0002_add_ingest_jobs
Revises: 0001_initial_schema
Create Date: 2026-06-12 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_add_ingest_jobs"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingest_jobs",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("total_chapters", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "current_phase",
            sa.String(length=20),
            nullable=False,
            server_default="phase0",
        ),
        sa.Column("phase0_result", sa.JSON(), nullable=True),
        sa.Column("phase1_result", sa.JSON(), nullable=True),
        sa.Column("phase2_result", sa.JSON(), nullable=True),
        sa.Column("phase3_result", sa.JSON(), nullable=True),
        sa.Column(
            "progress_percent",
            sa.Float(precision=2),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ingest_jobs_project_id"),
        "ingest_jobs",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ingest_jobs_project_id"), table_name="ingest_jobs")
    op.drop_table("ingest_jobs")
