"""
Moling - Service Layer Package.

Services contain business logic, orchestrate DAO operations,
and raise ``AppError`` exceptions on failures.

All services are exposed as singleton instances for easy ``Depends()`` injection.
"""

from app.service.auth_service import _auth_service_instance
from app.service.project_service import project_service
from app.service.chapter_service import chapter_service
from app.service.generation_service import generation_service
from app.service.vault_service import vault_service
from app.service.secret_service import secret_service

__all__ = [
    "auth_service",
    "project_service",
    "chapter_service",
    "generation_service",
    "vault_service",
    "secret_service",
]
