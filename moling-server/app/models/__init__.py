"""墨灵 (Moling) — ORM Models Package.

All models are imported here so Alembic's ``--autogenerate`` can discover them.
"""

from app.models.base import Base, BaseModel, TimestampMixin
from app.models.user import User
from app.models.project import Project
from app.models.chapter import Chapter
from app.models.dynamic_layer import DynamicLayer
from app.models.generation_task import GenerationTask
from app.models.card_pool import CardPool
from app.models.draw_history import DrawHistory
from app.models.vault_character import VaultCharacter
from app.models.vault_timeline import VaultTimeline
from app.models.vault_plot_promise import VaultPlotPromise
from app.models.vault_world import VaultWorld
from app.models.vault_changelog import VaultChangelog
from app.models.health_alert import HealthAlert
from app.models.system_config import SystemConfig
from app.models.secret import Secret
from app.models.notification import Notification
from app.models.subscription import Plan
from app.models.phase4_task import Phase4Task

__all__ = [
    "Base",
    "BaseModel",
    "TimestampMixin",
    "User",
    "Project",
    "Chapter",
    "DynamicLayer",
    "GenerationTask",
    "CardPool",
    "DrawHistory",
    "VaultCharacter",
    "VaultTimeline",
    "VaultPlotPromise",
    "VaultWorld",
    "VaultChangelog",
    "HealthAlert",
    "SystemConfig",
    "Secret",
    "Notification",
    "Plan",
    "Phase4Task",
]
