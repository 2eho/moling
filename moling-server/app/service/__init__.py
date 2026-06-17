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
    from app.service.vault_filter import VaultFilterService, vault_filter_service
except ImportError:
    VaultFilterService = None  # type: ignore[assignment]
    vault_filter_service = None

try:
    from app.service.conflict_detection import ConflictDetectionService, conflict_detection_service
except ImportError:
    ConflictDetectionService = None  # type: ignore[assignment]
    conflict_detection_service = None

try:
    from app.service.direction_scoring import DirectionScoringService, direction_scoring_service
except ImportError:
    DirectionScoringService = None  # type: ignore[assignment]
    direction_scoring_service = None

try:
    from app.service.weaving_scheme import WeavingSchemeService, weaving_scheme_service
except ImportError:
    WeavingSchemeService = None  # type: ignore[assignment]
    weaving_scheme_service = None

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

try:
    from app.service.phase4_service import Phase4Service, phase4_service
except ImportError:
    Phase4Service = None  # type: ignore[assignment]
    phase4_service = None

try:
    from app.service.phase4_scheduler import Phase4Scheduler, phase4_scheduler
except ImportError:
    Phase4Scheduler = None  # type: ignore[assignment]
    phase4_scheduler = None

try:
    from app.service.health_monitor import HealthMonitorService, health_monitor_service
except ImportError:
    HealthMonitorService = None  # type: ignore[assignment]
    health_monitor_service = None

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
