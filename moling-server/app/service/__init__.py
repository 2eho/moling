"""
Moling - Service Layer Package.

Services contain business logic, orchestrate DAO operations,
and raise ``AppError`` exceptions on failures.

All services are exposed as singleton instances for easy ``Depends()`` injection.
"""

from app.service.auth_service import _auth_service_instance
from app.service.project_service import project_service
from app.service.chapter_service import chapter_service
from app.service.card_service import card_service
from app.service.generation_service import generation_service
from app.service.vault_service import vault_service
from app.service.secret_service import secret_service
from app.service.prompt_service import prompt_service
from app.service.algorithm_service import algorithm_service
from app.service.validation_service import validation_service
from app.service.health_service import health_service

try:
    from app.service.import_service import import_service
except ImportError:
    import_service = None

try:
    from app.service.book_analysis_service import book_analysis_service
except ImportError:
    book_analysis_service = None

try:
    from app.service.card_pool_service import CardPoolService, card_pool_service
except ImportError:
    CardPoolService = None  # type: ignore[assignment]
    card_pool_service = None

__all__ = [
    "auth_service",
    "project_service",
    "chapter_service",
    "card_service",
    "generation_service",
    "vault_service",
    "secret_service",
    "prompt_service",
    "algorithm_service",
    "validation_service",
    "health_service",
    "import_service",
    "book_analysis_service",
    "CardPoolService",
    "card_pool_service",
]
