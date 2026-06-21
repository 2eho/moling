"""墨灵 (Moling) — S5: Add role column to users table

Separates the dual-purpose ``status`` field into:
- ``status`` — account state only (active / disabled / banned)
- ``role`` — user role (user / admin)

The ``require_admin`` dependency now checks ``role == "admin"`` instead of
``status == "admin"``.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add role column to users table, migrate existing admins."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("role", sa.String(20), nullable=False, server_default="user",
                      comment="用户角色: user / admin")
        )
    # Migrate existing admins: if status == "admin", set role = "admin"
    op.execute("UPDATE users SET role = 'admin' WHERE status = 'admin'")


def downgrade() -> None:
    """Drop the role column."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("role")
