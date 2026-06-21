"""rename_tables_to_plural

将 5 个表名修正为复数形式：
- vault_world → vault_worlds
- draw_history → draw_histories
- card_pool → card_pools
- vault_changelog → vault_changelogs
- system_config → system_configs

Revision ID: c8e0a2417478
Revises: 0007
Create Date: 2026-06-21 13:31:01.341755
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c8e0a2417478'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("vault_world", "vault_worlds")
    op.rename_table("draw_history", "draw_histories")
    op.rename_table("card_pool", "card_pools")
    op.rename_table("vault_changelog", "vault_changelogs")
    op.rename_table("system_config", "system_configs")


def downgrade() -> None:
    op.rename_table("vault_worlds", "vault_world")
    op.rename_table("draw_histories", "draw_history")
    op.rename_table("card_pools", "card_pool")
    op.rename_table("vault_changelogs", "vault_changelog")
    op.rename_table("system_configs", "system_config")
