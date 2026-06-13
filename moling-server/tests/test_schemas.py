"""墨灵 (Moling) — Schema Pydantic 验证测试。

覆盖 auth / project / chapter / card / generation / common 模块的
所有公开 Schema，包含有效数据与无效数据测试。
"""

import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginReq, RefreshReq, RegisterReq, TokenResp, UserResp
from app.schemas.chapter import ChapterResp, CreateChapterReq, UpdateChapterReq
from app.schemas.common import PaginatedResp, PaginationReq, SuccessResp
from app.schemas.generation import GenerateReq, GenerationResp, TaskStatusResp
from app.schemas.project import (
    CreateProjectReq,
    ProjectResp,
    ProjectStatsResp,
    UpdateProjectReq,
)
from app.schemas.card import CardResp, DrawCardReq, DrawCardResp


# ============================================================================
# Auth Schemas
# ============================================================================


class TestRegisterReq:
    def test_valid(self):
        req = RegisterReq(
            email="user@example.com", nickname="testuser", password="password123"
        )
        assert req.email == "user@example.com"
        assert req.nickname == "testuser"
        assert req.password == "password123"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            RegisterReq(
                email="not-an-email", username="testuser", password="password123"
            )

    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            RegisterReq(email="a@b.com", username="testuser", password="1234567")

    def test_username_too_short(self):
        with pytest.raises(ValidationError):
            RegisterReq(email="a@b.com", username="x", password="password123")

    def test_missing_fields(self):
        with pytest.raises(ValidationError):
            RegisterReq()


class TestLoginReq:
    def test_valid(self):
        req = LoginReq(email="user@example.com", password="secret")
        assert req.email == "user@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginReq(email="bad", password="secret")


class TestRefreshReq:
    def test_valid(self):
        req = RefreshReq(refresh_token="some-token-string")
        assert req.refresh_token == "some-token-string"

    def test_empty_token(self):
        """空字符串不会触发验证错误（需要额外的 min_length 约束）。"""
        req = RefreshReq(refresh_token="")
        assert req.refresh_token == ""


class TestUserResp:
    def test_from_attributes(self):
        """验证 model_config 启用了 from_attributes。"""
        assert UserResp.model_config.get("from_attributes") is True


class TestTokenResp:
    def test_valid(self):
        from datetime import datetime

        user = UserResp(
            id="1",
            email="a@b.com",
            username="u",
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        token = TokenResp(
            access_token="at", refresh_token="rt", user=user
        )
        assert token.user.email == "a@b.com"


# ============================================================================
# Project Schemas
# ============================================================================


class TestCreateProjectReq:
    def test_valid(self):
        req = CreateProjectReq(
            title="我的小说",
            author="作者名",
            genre="玄幻",
            creation_mode="from_scratch",
        )
        assert req.title == "我的小说"
        assert req.creation_mode == "from_scratch"

    def test_empty_title(self):
        with pytest.raises(ValidationError):
            CreateProjectReq(
                title="", author="作者", genre="玄幻", creation_mode="from_scratch"
            )

    def test_invalid_creation_mode(self):
        with pytest.raises(ValidationError):
            CreateProjectReq(
                title="小说", author="作者", genre="玄幻", creation_mode="invalid_mode"
            )

    def test_with_optional_fields(self):
        req = CreateProjectReq(
            title="小说",
            author="作者",
            genre="科幻",
            creation_mode="from_scratch",
            tags=["tag1", "tag2"],
            synopsis="简介内容",
            target_words=50000,
        )
        assert req.tags == ["tag1", "tag2"]
        assert req.target_words == 50000


class TestUpdateProjectReq:
    def test_valid_partial(self):
        req = UpdateProjectReq(title="新标题")
        assert req.title == "新标题"

    def test_valid_all_optional(self):
        req = UpdateProjectReq()
        assert req.title is None

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            UpdateProjectReq(status="invalid_status")


class TestProjectResp:
    def test_from_attributes(self):
        assert ProjectResp.model_config.get("from_attributes") is True


class TestProjectStatsResp:
    def test_defaults(self):
        stats = ProjectStatsResp()
        assert stats.total_projects == 0
        assert stats.active_count == 0
        assert stats.draft_count == 0
        assert stats.total_words == 0


# ============================================================================
# Chapter Schemas
# ============================================================================


class TestCreateChapterReq:
    def test_valid(self):
        req = CreateChapterReq(title="第一章", chapter_number=1)
        assert req.chapter_number == 1

    def test_invalid_chapter_number(self):
        with pytest.raises(ValidationError):
            CreateChapterReq(title="第一章", chapter_number=0)


class TestUpdateChapterReq:
    def test_valid(self):
        req = UpdateChapterReq(content="正文内容")
        assert req.content == "正文内容"


class TestChapterResp:
    def test_from_attributes(self):
        assert ChapterResp.model_config.get("from_attributes") is True


# ============================================================================
# Card Schemas
# ============================================================================


class TestDrawCardReq:
    def test_valid(self):
        req = DrawCardReq(keep_card_ids=[1], weights=[0.5], mode="single")
        assert req.mode == "single"

    def test_invalid_mode(self):
        with pytest.raises(ValidationError):
            DrawCardReq(keep_card_ids=[], weights=[], mode="unknown")


class TestCardResp:
    def test_from_attributes(self):
        assert CardResp.model_config.get("from_attributes") is True


# ============================================================================
# Generation Schemas
# ============================================================================


class TestGenerateReq:
    def test_valid(self):
        req = GenerateReq(card_ids=[1, 2], weights=[0.5, 0.5], mode="hybrid")
        assert req.mode == "hybrid"

    def test_invalid_mode(self):
        with pytest.raises(ValidationError):
            GenerateReq(card_ids=[], weights=[], mode="bad")

    def test_defaults(self):
        req = GenerateReq()
        assert req.card_ids == []
        assert req.weights == []
        assert req.mode == "single"


class TestGenerationResp:
    def test_valid(self):
        resp = GenerationResp(task_id="uuid-123")
        assert resp.task_id == "uuid-123"
        assert resp.status == "pending"


class TestTaskStatusResp:
    def test_valid(self):
        resp = TaskStatusResp(task_id="uuid-456", status="running")
        assert resp.status == "running"


# ============================================================================
# Common Schemas
# ============================================================================


class TestPaginationReq:
    def test_defaults(self):
        req = PaginationReq()
        assert req.page == 1
        assert req.page_size == 20

    def test_custom_values(self):
        req = PaginationReq(page=3, page_size=50)
        assert req.page == 3

    def test_invalid_page(self):
        with pytest.raises(ValidationError):
            PaginationReq(page=0)

    def test_invalid_page_size_too_large(self):
        with pytest.raises(ValidationError):
            PaginationReq(page_size=200)

    def test_invalid_page_size_too_small(self):
        with pytest.raises(ValidationError):
            PaginationReq(page_size=0)


class TestPaginatedResp:
    def test_valid(self):
        resp = PaginatedResp[int](items=[1, 2], total=2, page=1, page_size=20)
        assert resp.total == 2

    def test_defaults(self):
        resp = PaginatedResp[int]()
        assert resp.items == []
        assert resp.total == 0


class TestSuccessResp:
    def test_defaults(self):
        resp = SuccessResp()
        assert resp.code == 200
        assert resp.message == "success"

    def test_custom(self):
        resp = SuccessResp(code=201, message="created", data={"id": 1})
        assert resp.data["id"] == 1
