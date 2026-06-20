"""
Moling - Service Layer Package.

Services contain business logic, orchestrate DAO operations,
and raise ``AppError`` exceptions on failures.

All services are exposed as singleton instances for easy ``Depends()`` injection.
"""

from app.service.auth_service import auth_service
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

from app.service.vault_filter import VaultFilterService, vault_filter_service
from app.service.conflict_detection import ConflictDetectionService, conflict_detection_service
from app.service.direction_scoring import DirectionScoringService, direction_scoring_service
from app.service.weaving_scheme import WeavingSchemeService, weaving_scheme_service
from app.service.import_service import import_service
from app.service.book_analysis_service import book_analysis_service
from app.service.card_pool_service import CardPoolService, card_pool_service
from app.service.phase4_service import Phase4Service, phase4_service
from app.service.phase4_scheduler import Phase4Scheduler, phase4_scheduler
from app.service.health_monitor import HealthMonitorService, health_monitor_service

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
    "VaultFilterService",
    "vault_filter_service",
    "ConflictDetectionService",
    "conflict_detection_service",
    "DirectionScoringService",
    "direction_scoring_service",
    "WeavingSchemeService",
    "weaving_scheme_service",
    "Phase4Service",
    "phase4_service",
    "Phase4Scheduler",
    "phase4_scheduler",
    "HealthMonitorService",
    "health_monitor_service",
]
