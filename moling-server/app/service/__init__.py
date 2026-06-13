"""
Moling - Service Layer Package.

Services contain business logic, orchestrate DAO operations,
and raise ``AppError`` exceptions on failures.

Note: Service instances should be injected via ``Depends()`` in routers.
      Import the classes here; use ``get_xxx_service()`` from ``dependencies``.
"""

from app.service.auth_service import AuthService
from app.service.project_service import ProjectService
from app.service.chapter_service import ChapterService
from app.service.generation_service import GenerationService
from app.service.vault_service import VaultService
from app.service.secret_service import SecretService

__all__ = [
    "AuthService",
    "ProjectService",
    "ChapterService",
    "GenerationService",
    "VaultService",
    "SecretService",
]
