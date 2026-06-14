"""Moling - Auth Service.

Handles user registration (password hashing), login (credential verification + JWT
issuance), token refresh, and current-user retrieval.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session as SyncSession

from app.config import get_settings
from app.dao import user_dao
from app.errors import AuthError, ConflictError, ErrorCode, NotFoundError
from app.schemas.auth import LoginReq, PasswordResetReq, PasswordResetRequestReq, RegisterReq, TokenResp, UserResp

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
# Password reset token helper
# ---------------------------------------------------------------------------


def _generate_reset_token() -> str:
    """Generate a secure random reset token."""
    return secrets.token_urlsafe(32)


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


async def request_password_reset(db: AsyncSession, req: PasswordResetRequestReq) -> dict:
    """Request password reset (generate token)."""
    return await _get_auth_service().request_password_reset(db, req)


async def reset_password(db: AsyncSession, req: PasswordResetReq) -> dict:
    """Reset password using token."""
    return await _get_auth_service().reset_password(db, req)


async def update_profile(db: AsyncSession, user_id: int, req) -> UserResp:
    """Update user profile."""
    return await _get_auth_service().update_profile(db, user_id, req)


# ---------------------------------------------------------------------------
# Sync versions (for Windows + aiosslite workaround)
# ---------------------------------------------------------------------------

def register_sync(db: SyncSession, req: RegisterReq) -> TokenResp:
    """Register a new user and return tokens (sync version)."""
    return _get_auth_service().register_sync(db, req)


def login_sync(db: SyncSession, req: LoginReq) -> TokenResp:
    """Login with email + password, return tokens (sync version)."""
    return _get_auth_service().login_sync(db, req)


class AuthService:
    """Service for authentication operations."""

    async def request_password_reset(self, db: AsyncSession, req: PasswordResetRequestReq) -> dict:
        """Request password reset.
        
        Generates a reset token and stores it in the user record.
        In production, this token would be sent via email.
        For now, we return it in the response for testing.
        """
        # Find user by email
        user = await user_dao.get_by_email(db, req.email)
        if user is None:
            # Don't reveal that email doesn't exist (security)
            return {"message": "If the email exists, a reset link has been sent."}
        
        # Generate reset token
        reset_token = _generate_reset_token()
        reset_expires = datetime.now(timezone.utc) + timedelta(hours=24)  # Token valid for 24 hours
        
        # Store token in user record
        user.reset_token = reset_token
        user.reset_token_expires = reset_expires
        
        await db.commit()
        
        # TODO: In production, send email with reset link
        # For now, return token in response (for testing only)
        return {
            "message": "Password reset requested.",
            "reset_token": reset_token,  # TODO: Remove in production
        }

    async def reset_password(self, db: AsyncSession, req: PasswordResetReq) -> dict:
        """Reset password using token."""
        # Find user by reset token
        from app.models import User
        from sqlalchemy import select
        
        stmt = select(User).where(User.reset_token == req.token)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None:
            raise AuthError(
                error_code=ErrorCode.AUTH_INVALID_TOKEN,
                detail="Invalid or expired reset token",
            )
        
        # Check if token is expired
        if user.reset_token_expires is None or user.reset_token_expires < datetime.now(timezone.utc):
            raise AuthError(
                error_code=ErrorCode.AUTH_INVALID_TOKEN,
                detail="Invalid or expired reset token",
            )
        
        # Reset password
        user.password_hash = _hash_password(req.new_password)
        
        # Clear reset token
        user.reset_token = None
        user.reset_token_expires = None
        
        await db.commit()
        
        return {"message": "Password reset successful."}

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

    # ------------------------------------------------------------------
    # Sync versions (for Windows + aiosslite workaround)
    # ------------------------------------------------------------------

    def register_sync(self, db: SyncSession, req: RegisterReq) -> TokenResp:
        """Sync version — use with get_sync_db()."""
        dao = user_dao.UserDAO()
        # Check uniqueness (sync)
        existing_email = dao.get_by_email_sync(db, req.email)
        if existing_email:
            from app.errors import ConflictError, ErrorCode
            raise ConflictError(
                error_code=ErrorCode.USER_EMAIL_EXISTS,
                detail="Email already registered",
            )
        existing_username = dao.get_by_username_sync(db, req.nickname)
        if existing_username:
            from app.errors import ConflictError, ErrorCode
            raise ConflictError(
                error_code=ErrorCode.USER_USERNAME_EXISTS,
                detail="Username already taken",
            )

        # Create user (sync)
        from app.models.user import User
        user = User(
            email=req.email,
            username=req.nickname,
            password_hash=_hash_password(req.password),
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create tokens
        access_token = _create_access_token(user.id)
        refresh_token = _create_refresh_token(user.id)

        return TokenResp(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=15 * 60,
            user=UserResp.model_validate(user),
        )

    def login_sync(self, db: SyncSession, req: LoginReq) -> TokenResp:
        """Sync version — use with get_sync_db()."""
        dao = user_dao.UserDAO()
        user = dao.get_by_email_sync(db, req.email)
        if user is None:
            from app.errors import AuthError, ErrorCode
            raise AuthError(
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                detail="Invalid email or password",
            )
        if not _verify_password(req.password, user.password_hash):
            from app.errors import AuthError, ErrorCode
            raise AuthError(
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                detail="Invalid email or password",
            )
        if user.status != "active":
            from app.errors import AuthError, ErrorCode
            raise AuthError(
                error_code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
                detail="Account is disabled",
            )

        access_token = _create_access_token(user.id)
        refresh_token = _create_refresh_token(user.id)

        return TokenResp(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
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

    async def update_profile(self, db: AsyncSession, user_id: int, req) -> UserResp:
        """Update user profile (username, avatar_url)."""
        from app.schemas.auth import UpdateProfileReq
        
        user = await user_dao.get(db, user_id)
        if user is None:
            raise NotFoundError(
                error_code=ErrorCode.USER_NOT_FOUND,
                detail="User not found",
            )

        # Update fields if provided
        if isinstance(req, dict):
            update_data = req
        else:
            update_data = req.model_dump(exclude_unset=True)

        if "username" in update_data and update_data["username"] is not None:
            # Check username uniqueness
            existing = await user_dao.get_by_username(db, update_data["username"])
            if existing and existing.id != user_id:
                from app.errors import ConflictError
                raise ConflictError(
                    error_code=ErrorCode.USER_USERNAME_EXISTS,
                    detail="Username already taken",
                )
            user.username = update_data["username"]

        if "avatar_url" in update_data and update_data["avatar_url"] is not None:
            user.avatar_url = update_data["avatar_url"]

        await db.commit()
        await db.refresh(user)

        return UserResp.model_validate(user)
