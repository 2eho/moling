"""墨灵 (Moling) — Setting Service.

业务逻辑：获取设置、更新设置、修改密码等。
"""

from __future__ import annotations

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import user_dao
from app.errors import AuthError, ErrorCode, NotFoundError, ValidationError
from app.schemas.setting import UserSettings

settings = get_settings()

# Password hashing
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against its hash."""
    return _pwd_ctx.verify(plain, hashed)


def _hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return _pwd_ctx.hash(password)


class SettingService:
    """Service for user settings operations."""

    async def get_settings(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> UserSettings:
        """Get current user settings."""
        user = await user_dao.get(db, user_id)
        
        if user is None:
            raise NotFoundError(
                error_code=ErrorCode.USER_NOT_FOUND,
                detail="User not found",
            )
        
        # Parse settings from JSON field, use defaults if not set
        settings_dict = user.settings or {}
        return UserSettings(**settings_dict)

    async def update_settings(
        self,
        db: AsyncSession,
        user_id: str,
        settings_update: dict,
    ) -> UserSettings:
        """Update user settings (partial update)."""
        user = await user_dao.get(db, user_id)
        
        if user is None:
            raise NotFoundError(
                error_code=ErrorCode.USER_NOT_FOUND,
                detail="User not found",
            )
        
        # Get current settings
        current_settings = user.settings or {}
        
        # Update with new values (partial update)
        current_settings.update(settings_update)
        
        # Save back to user
        user.settings = current_settings
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise
        await db.refresh(user)
        
        return UserSettings(**current_settings)

    async def change_password(
        self,
        db: AsyncSession,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> dict:
        """Change user password (requires old password verification)."""
        user = await user_dao.get(db, user_id)
        
        if user is None:
            raise NotFoundError(
                error_code=ErrorCode.USER_NOT_FOUND,
                detail="User not found",
            )
        
        # Verify old password
        if not _verify_password(old_password, user.password_hash):
            raise AuthError(
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                detail="Old password is incorrect",
            )
        
        # Validate new password
        if len(new_password) < 8:
            raise ValidationError(
                error_code=ErrorCode.VALIDATION_ERROR,
                detail="New password must be at least 8 characters",
            )
        
        # Update password
        user.password_hash = _hash_password(new_password)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise
        
        return {"message": "密码修改成功"}

    async def get_profile(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> dict:
        """Get user profile information."""
        user = await user_dao.get(db, user_id)
        
        if user is None:
            raise NotFoundError(
                error_code=ErrorCode.USER_NOT_FOUND,
                detail="User not found",
            )
        
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "status": user.status,
            "created_at": user.created_at,
        }

    async def update_profile(
        self,
        db: AsyncSession,
        user_id: str,
        *,
        username: str | None = None,
        bio: str | None = None,
        avatar_url: str | None = None,
    ) -> dict:
        """Update user profile."""
        user = await user_dao.get(db, user_id)
        
        if user is None:
            raise NotFoundError(
                error_code=ErrorCode.USER_NOT_FOUND,
                detail="User not found",
            )
        
        # Check username uniqueness if changing
        if username and username != user.username:
            existing = await user_dao.get_by_username(db, username)
            if existing:
                raise ValidationError(
                    error_code=ErrorCode.USER_USERNAME_EXISTS,
                    detail="Username already taken",
                )
            user.username = username
        
        if bio is not None:
            user.bio = bio
        
        if avatar_url is not None:
            user.avatar_url = avatar_url
        
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise
        await db.refresh(user)
        
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "status": user.status,
            "created_at": user.created_at,
        }


# Singleton instance
setting_service = SettingService()
