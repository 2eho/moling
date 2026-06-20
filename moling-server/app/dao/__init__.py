"""Moling - Data Access Object Package."""

from app.dao.base_dao import BaseDAO
from app.dao.user_dao import UserDAO
from app.dao.secret_dao import SecretDAO
from app.dao.project_dao import ProjectDAO
from app.dao.chapter_dao import ChapterDAO
from app.dao.vault_dao import VaultDAO
from app.dao.card_dao import CardDAO
from app.dao.generation_dao import GenerationDAO
from app.dao.notification_dao import NotificationDAO
from app.dao.template_dao import TemplateDAO
from app.dao.phase4_dao import Phase4DAO
from app.dao.dynamic_layer_dao import DynamicLayerDAO
from app.dao.health_alert_dao import HealthAlertDAO
from app.dao.system_config_dao import SystemConfigDAO
from app.dao.subscription_dao import PlanDAO, UserSubscriptionDAO, plan_dao, user_subscription_dao

# Singleton DAO instances (shared across the application)
user_dao = UserDAO()
project_dao = ProjectDAO()
chapter_dao = ChapterDAO()
vault_dao = VaultDAO()
card_dao = CardDAO()
generation_dao = GenerationDAO()
notification_dao = NotificationDAO()
template_dao = TemplateDAO()
phase4_dao = Phase4DAO()
dynamic_layer_dao = DynamicLayerDAO()
secret_dao = SecretDAO()
health_alert_dao = HealthAlertDAO()
system_config_dao = SystemConfigDAO()

__all__ = [
    "BaseDAO",
    "UserDAO",
    "ProjectDAO",
    "ChapterDAO",
    "VaultDAO",
    "CardDAO",
    "GenerationDAO",
    "NotificationDAO",
    "TemplateDAO",
    "Phase4DAO",
    "DynamicLayerDAO",
    "SecretDAO",
    "HealthAlertDAO",
    "SystemConfigDAO",
    "PlanDAO",
    "UserSubscriptionDAO",
    "user_dao",
    "project_dao",
    "chapter_dao",
    "vault_dao",
    "card_dao",
    "generation_dao",
    "notification_dao",
    "template_dao",
    "phase4_dao",
    "dynamic_layer_dao",
    "secret_dao",
    "health_alert_dao",
    "system_config_dao",
    "plan_dao",
    "user_subscription_dao",
]
