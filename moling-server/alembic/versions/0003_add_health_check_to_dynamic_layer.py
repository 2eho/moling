"""添加 health_check 字段到 dynamic_layers 表

Revision ID: 0003
Revises: 0002
Create Date: 2025-01-01

参考文档: 009_2b7b5b03_moling-card-combination-algorithm.md §5.3.5
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002_add_ingest_jobs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加 health_check 字段到 dynamic_layers 表."""
    op.add_column(
        'dynamic_layers',
        sa.Column('health_check', JSONB(), nullable=True)
    )


def downgrade() -> None:
    """删除 health_check 字段."""
    op.drop_column('dynamic_layers', 'health_check')
