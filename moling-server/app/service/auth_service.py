"""Moling - Auth Service.

Handles user registration (password hashing), login (credential verification + JWT
issuance), token refresh, and current-user retrieval.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

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

def _create_access_token(user_id: int) -> tuple[str, str, int]:
    """Create a short-lived access token (15 min).
    
    Returns:
        tuple: (token, jti, expires_in)
    """
    import uuid
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    jti = str(uuid.uuid4())
    to_encode = {"sub": str(user_id), "type": "access", "exp": expire, "jti": jti}
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, 15 * 60


def _create_refresh_token(user_id: int) -> tuple[str, str, int]:
    """Create a long-lived refresh token (30 days).
    
    Returns:
        tuple: (token, jti, expires_in)
    """
    import uuid
    
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    jti = str(uuid.uuid4())
    to_encode = {"sub": str(user_id), "type": "refresh", "exp": expire, "jti": jti}
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, 30 * 24 * 60 * 60


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


async def logout(access_token: str, refresh_token: str) -> dict:
    """Logout user by adding tokens to blacklist."""
    return await _get_auth_service().logout(access_token, refresh_token)


# ---------------------------------------------------------------------------
# Sync versions (for Windows + aiosslite workaround)
# ---------------------------------------------------------------------------

def register_sync(db, req: RegisterReq) -> TokenResp:
    """Register a new user and return tokens (sync version)."""
    return _get_auth_service().register_sync(db, req)


def login_sync(db, req: LoginReq) -> TokenResp:
    """Login with email + password, return tokens (sync version)."""
    return _get_auth_service().login_sync(db, req)


class AuthService:
    """Service for authentication operations."""

    async def request_password_reset(self, db: AsyncSession, req: PasswordResetRequestReq) -> dict:
        """Request password reset.
        
        Generates a reset token and stores it in the user record.
        In production, this token must be sent via email — never returned
        in the API response body, as doing so exposes the token to:
        1) Network intermediaries (proxy, CDN logs)
        2) Browser history / referrer headers
        3) Server access logs
        
        Security requirement: reset_token MUST only be delivered through
        the out-of-band email channel, not in the API response.
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
        
        # SECURITY: reset_token 不得通过 API 响应返回。
        # 生产环境中应通过邮件发送重置链接（包含 token），
        # 防止 token 被中介层（代理、CDN、日志）捕获。
        # 以下仅保留 token 前 4 位用于测试验证（开发环境临时方案）。
        return {
            "message": "If the email exists, a reset link has been sent.",
            # WARNING: 以下信息仅在开发/测试环境暴露，生产部署前必须删除
            "reset_token_prefix": reset_token[:4] + "...",
            "reset_token_expires": reset_expires.isoformat(),
        }

    async def reset_password(self, db: AsyncSession, req: PasswordResetReq) -> dict:
        """Reset password using token (via DAO)."""
        user = await user_dao.get_by_reset_token(db, req.token)
        
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
        access_token, access_jti, access_expires = _create_access_token(user.id)
        refresh_token, refresh_jti, refresh_expires = _create_refresh_token(user.id)

        return TokenResp(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",  # nosec B106
            expires_in=access_expires,
            user=UserResp.model_validate(user),
        )

    # ------------------------------------------------------------------
    # Sync versions (for Windows + aiosslite workaround)
    # ------------------------------------------------------------------

    def register_sync(self, db, req: RegisterReq) -> TokenResp:
        """Sync version — use with get_sync_db()."""
        from sqlalchemy.orm import Session as SyncSession  # noqa: F811 — Windows compatibility
        dao = user_dao
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
        access_token, access_jti, access_expires = _create_access_token(user.id)
        refresh_token, refresh_jti, refresh_expires = _create_refresh_token(user.id)

        return TokenResp(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=access_expires,
            user=UserResp.model_validate(user),
        )

    def login_sync(self, db, req: LoginReq) -> TokenResp:
        """Sync version — use with get_sync_db()."""
        from sqlalchemy.orm import Session as SyncSession  # noqa: F811 — Windows compatibility
        dao = user_dao
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

        access_token, access_jti, access_expires = _create_access_token(user.id)
        refresh_token, refresh_jti, refresh_expires = _create_refresh_token(user.id)

        return TokenResp(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=access_expires,
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
        access_token, access_jti, access_expires = _create_access_token(user.id)
        refresh_token, refresh_jti, refresh_expires = _create_refresh_token(user.id)

        return TokenResp(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",  # nosec B106
            expires_in=access_expires,
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
        access_token, access_jti, access_expires = _create_access_token(user.id)
        new_refresh_token, refresh_jti, refresh_expires = _create_refresh_token(user.id)

        return TokenResp(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",  # nosec B106
            expires_in=access_expires,
            user=UserResp.model_validate(user),
        )

    async def logout(self, access_token: str, refresh_token: str) -> dict:
        """Logout user by adding tokens to blacklist.
        
        Args:
            access_token: JWT access token
            refresh_token: JWT refresh token
            
        Returns:
            dict: Success message
        """
        from app.auth.blacklist import add_to_blacklist
        
        # Decode tokens to get JTI and expiry
        try:
            access_payload = jwt.decode(
                access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            refresh_payload = jwt.decode(
                refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            
            # Add to blacklist with remaining TTL
            access_jti = access_payload.get("jti")
            refresh_jti = refresh_payload.get("jti")
            
            if access_jti:
                # Calculate remaining TTL for access token
                access_exp = access_payload.get("exp", 0)
                access_ttl = max(0, int(access_exp - datetime.now(timezone.utc).timestamp()))
                add_to_blacklist(access_jti, access_ttl)
            
            if refresh_jti:
                # Calculate remaining TTL for refresh token
                refresh_exp = refresh_payload.get("exp", 0)
                refresh_ttl = max(0, int(refresh_exp - datetime.now(timezone.utc).timestamp()))
                add_to_blacklist(refresh_jti, refresh_ttl)
                
        except JWTError:
            # Token already invalid, nothing to do
            pass
        
        return {"message": "Successfully logged out"}

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
