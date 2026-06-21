"""墨灵 (Moling) — Pydantic Schema Package."""

from app.schemas.common import (
    PaginationReq,
    PaginatedResp,
    SuccessResp,
)
from app.schemas.auth import (
    RegisterReq,
    LoginReq,
    TokenResp,
    RefreshReq,
    UserResp,
)
from app.schemas.project import (
    CreateProjectReq,
    UpdateProjectReq,
    ProjectResp,
    ProjectStatsResp,
)
from app.schemas.chapter import (
    CreateChapterReq,
    UpdateChapterReq,
    ChapterResp,
)
from app.schemas.card import (
    DrawCardReq,
    DrawCardResp,
    CardResp,
)
from app.schemas.vault import (
    CharacterResp,
    TimelineResp,
    PlotPromiseResp,
    WorldResp,
)
from app.schemas.generation import (
    GenerateReq,
    GenerationResp,
    TaskStatusResp,
)
from app.schemas.health import (
    HealthAlertResp,
)
from app.schemas.template import (
    TemplateResp,
)
from app.schemas.secret import (
    SecretResp,
    UpdateSecretReq,
)
from app.schemas.ingest import (
    IngestStartResp,
    IngestJobStatusResp,
    IngestJobListResp,
    PhaseRunResp,
    PhaseStatusResp,
    FullImportResp,
)
from app.schemas.notification import (
    NotificationResp,
)
from app.schemas.subscription import (
    PlanResp,
)
from app.schemas.coherence import (
    CoherenceCheckItem,
    CoherenceGroupCheck,
    CoherenceValidationResult,
    CoherencePipelineResult,
    GROUP_DEFINITIONS,
)
from app.schemas.admin import (
    SystemStatsResp,
    LlmUsageResp,
    LLMConfigReq,
    LLMConfigResp,
    AdminStatsResp,
    UserManageResp,
    ProjectManageResp,
    UpdateUserReq,
)
from app.schemas.phase4 import (
    Phase4SuggestionResp,
    ApplyPhase4Req,
    RejectReviewReq,
    Phase4TaskResp,
)
from app.schemas.setting import (
    UserSettings,
    HealthMonitorReq,
    Phase4ReviewReq,
    Phase4ModeReq,
    ChangePasswordReq,
    UpdateProfileReq,
)
from app.schemas.weave import (
    WeaveSuggestionResp,
    ApplyWeaveReq,
    WeaveAnalysisResp,
)

__all__ = [
    # common
    "PaginationReq",
    "PaginatedResp",
    "SuccessResp",
    # auth
    "RegisterReq",
    "LoginReq",
    "TokenResp",
    "RefreshReq",
    "UserResp",
    # project
    "CreateProjectReq",
    "UpdateProjectReq",
    "ProjectResp",
    "ProjectStatsResp",
    # chapter
    "CreateChapterReq",
    "UpdateChapterReq",
    "ChapterResp",
    # card
    "DrawCardReq",
    "DrawCardResp",
    "CardResp",
    # vault
    "CharacterResp",
    "TimelineResp",
    "PlotPromiseResp",
    "WorldResp",
    # generation
    "GenerateReq",
    "GenerationResp",
    "TaskStatusResp",
    # health
    "HealthAlertResp",
    # template
    "TemplateResp",
    # secret
    "SecretResp",
    "UpdateSecretReq",
    # ingest
    "IngestStartResp",
    "IngestJobStatusResp",
    "IngestJobListResp",
    "PhaseRunResp",
    "PhaseStatusResp",
    "FullImportResp",
    # notification
    "NotificationResp",
    # subscription
    "PlanResp",
    # coherence
    "CoherenceCheckItem",
    "CoherenceGroupCheck",
    "CoherenceValidationResult",
    "CoherencePipelineResult",
    "GROUP_DEFINITIONS",
    # admin
    "SystemStatsResp",
    "LlmUsageResp",
    "LLMConfigReq",
    "LLMConfigResp",
    "AdminStatsResp",
    "UserManageResp",
    "ProjectManageResp",
    "UpdateUserReq",
    # phase4
    "Phase4SuggestionResp",
    "ApplyPhase4Req",
    "RejectReviewReq",
    "Phase4TaskResp",
    # setting
    "UserSettings",
    "HealthMonitorReq",
    "Phase4ReviewReq",
    "Phase4ModeReq",
    "ChangePasswordReq",
    "UpdateProfileReq",
    # weave
    "WeaveSuggestionResp",
    "ApplyWeaveReq",
    "WeaveAnalysisResp",
]
