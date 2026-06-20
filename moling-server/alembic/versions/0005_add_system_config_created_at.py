"""墨灵 (Moling) — Add created_at to system_config

Adds the missing ``created_at`` timestamp column to the ``system_config`` table
to align with the model's ``TimestampMixin`` (added in MM9 fix).

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "system_config",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="创建时间",
        ),
    )


def downgrade() -> None:
    op.drop_column("system_config", "created_at")
