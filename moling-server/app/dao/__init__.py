"""Moling - Data Access Object Package."""

from app.dao.base_dao import BaseDAO
from app.dao.user_dao import UserDAO
from app.dao.project_dao import ProjectDAO
from app.dao.chapter_dao import ChapterDAO
from app.dao.vault_dao import VaultDAO
from app.dao.card_dao import CardDAO
from app.dao.generation_dao import GenerationDAO
from app.dao.notification_dao import NotificationDAO
from app.dao.template_dao import TemplateDAO
from app.dao.phase4_dao import Phase4DAO

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
    "user_dao",
    "project_dao",
    "chapter_dao",
    "vault_dao",
    "card_dao",
    "generation_dao",
    "notification_dao",
    "template_dao",
    "phase4_dao",
]
