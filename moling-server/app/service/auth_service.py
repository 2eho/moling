"""Moling - Auth Service.

Handles user registration (password hashing), login (credential verification + JWT
issuance), token refresh, and current-user retrieval.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import user_dao
from app.errors import AuthError, ConflictError, ErrorCode, NotFoundError
from app.schemas.auth import LoginReq, RegisterReq, TokenResp, UserResp

settings = get_settings()

# ---------------------------------------------------------------------------
# Password hashing (bcrypt via passlib)
# ---------------------------------------------------------------------------

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return _pwd_ctx.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against its hash."""
    return _pwd_ctx.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def _create_access_token(user_id: int) -> str:
    """Create a short-lived access token (15 min)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode = {"sub": str(user_id), "type": "access", "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _create_refresh_token(user_id: int) -> str:
    """Create a long-lived refresh token (30 days)."""
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    to_encode = {"sub": str(user_id), "type": "refresh", "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ---------------------------------------------------------------------------
# Module-level functions (used by tests and routers)
# ---------------------------------------------------------------------------

_auth_service_instance = None


def _get_auth_service():
    """Get or create AuthService instance."""
    global _auth_service_instance
    if _auth_service_instance is None:
        _auth_service_instance = AuthService()
    return _auth_service_instance


async def register(db: AsyncSession, req: RegisterReq) -> TokenResp:
    """Register a new user and return tokens."""
    return await _get_auth_service().register(db, req)


async def login(db: AsyncSession, req: LoginReq) -> TokenResp:
    """Login with email + password, return tokens."""
    return await _get_auth_service().login(db, req)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResp:
    """Refresh access token using refresh token."""
    return await _get_auth_service().refresh_tokens(db, refresh_token)


async def get_current_user(db: AsyncSession, user_id: int) -> UserResp:
    """Return full user info from the database by user id."""
    return await _get_auth_service().get_current_user(db, user_id)


class AuthService:
    """Service for authentication operations."""

    async def register(self, db: AsyncSession, req: RegisterReq) -> TokenResp:
        """Register a new user and return tokens."""
        # Check uniqueness
        existing_email = await user_dao.get_by_email(db, req.email)
        if existing_email:
            raise ConflictError(
                error_code=ErrorCode.USER_EMAIL_EXISTS,
                detail="Email already registered",
            )

        existing_username = await user_dao.get_by_username(db, req.nickname)
        if existing_username:
            raise ConflictError(
                error_code=ErrorCode.USER_USERNAME_EXISTS,
                detail="Username already taken",
            )

        # Create user
        from app.models import User

        user = User(
            email=req.email,
            username=req.nickname,  # Use nickname as username
            password_hash=_hash_password(req.password),
            status="active",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Create tokens
        access_token = _create_access_token(user.id)
        refresh_token = _create_refresh_token(user.id)

        return TokenResp(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",  # nosec B106
            expires_in=15 * 60,
            user=UserResp.model_validate(user),
        )

    async def login(self, db: AsyncSession, req: LoginReq) -> TokenResp:
        """Login with email + password, return tokens."""
        user = await user_dao.get_by_email(db, req.email)
        if user is None:
            raise AuthError(
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                detail="Invalid email or password",
            )

        if not _verify_password(req.password, user.password_hash):
            raise AuthError(
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                detail="Invalid email or password",
            )

        if user.status != "active":
            raise AuthError(
                error_code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
                detail="Account is disabled",
            )

        # Create tokens
        access_token = _create_access_token(user.id)
        refresh_token = _create_refresh_token(user.id)

        return TokenResp(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",  # nosec B106
            expires_in=15 * 60,
            user=UserResp.model_validate(user),
        )

    async def refresh_tokens(self, db: AsyncSession, refresh_token: str) -> TokenResp:
        """Refresh access token using refresh token."""
        try:
            payload = jwt.decode(
                refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            if payload.get("type") != "refresh":
                raise AuthError(
                    error_code=ErrorCode.AUTH_INVALID_TOKEN,
                    detail="Invalid refresh token",
                )

            user_id = payload["sub"]
        except JWTError:
            raise AuthError(
                error_code=ErrorCode.AUTH_INVALID_TOKEN,
                detail="Invalid refresh token",
            )

        user = await user_dao.get(db, user_id)
        if user is None:
            raise NotFoundError(
                error_code=ErrorCode.USER_NOT_FOUND,
                detail="User not found",
            )

        # Create new tokens
        access_token = _create_access_token(user.id)
        new_refresh_token = _create_refresh_token(user.id)

        return TokenResp(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",  # nosec B106
            expires_in=15 * 60,
            user=UserResp.model_validate(user),
        )

    async def get_current_user(self, db: AsyncSession, user_id: int) -> UserResp:
        """Return full user info from the database by user id."""
        user = await user_dao.get(db, user_id)
        if user is None:
            raise NotFoundError(
                error_code=ErrorCode.USER_NOT_FOUND,
                detail="User not found",
            )
        return UserResp.model_validate(user)
