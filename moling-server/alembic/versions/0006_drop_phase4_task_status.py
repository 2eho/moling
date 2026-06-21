"""墨灵 (Moling) — P1-3: Drop Phase4Task.status, unify with state

Removes the redundant ``status`` column from ``phase4_tasks`` table.
All status tracking is now done via the ``state`` column using ``Phase4State`` enum.

Old status → state mapping:
- pending → idle
- analyzed → analyzed (new Phase4State value)
- running → extracting
- done → done
- failed → failed
- approved → approved (new Phase4State value)
- rejected → rejected (new Phase4State value)
- queued → queued (already a Phase4State value)

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the status column from phase4_tasks."""
    with op.batch_alter_table("phase4_tasks") as batch_op:
        batch_op.drop_column("status")


def downgrade() -> None:
    """Restore the status column (with default)."""
    with op.batch_alter_table("phase4_tasks") as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(20), nullable=False, server_default="pending")
        )
