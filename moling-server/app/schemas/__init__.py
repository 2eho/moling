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
from app.schemas.notification import (
    NotificationResp,
)
from app.schemas.subscription import (
    PlanResp,
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
    # notification
    "NotificationResp",
    # subscription
    "PlanResp",
]
