"""澧ㄧ伒 (Moling) 鈥?Secret (绉樺瘑鐭╅樀) Service Layer."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.secret import Secret
from app.models.vault_character import VaultCharacter
from app.schemas.secret import SecretResp, UpdateSecretReq, UpdateSecretsByCharacterReq


class SecretService:
    """Business logic for secret matrix operations."""

    @staticmethod
    async def list_secrets(
        db: AsyncSession,
        project_id: int,
    ) -> list[SecretResp]:
        """List all secrets for a project."""
        result = await db.execute(
            select(Secret)
            .where(Secret.project_id == project_id)
            .order_by(Secret.id)
        )
        secrets = result.scalars().all()
        return [SecretResp.model_validate(s) for s in secrets]

    @staticmethod
    async def get_secrets_by_character(
        db: AsyncSession,
        project_id: int,
        character_id: int,
    ) -> dict:
        """Get secrets known to and unknown by a specific character."""
        # First, get the character name by ID
        result = await db.execute(
            select(VaultCharacter).where(
                VaultCharacter.id == character_id,
                VaultCharacter.project_id == project_id,
            )
        )
        character = result.scalar_one_or_none()
        if character is None:
            return {
                "character_id": character_id,
                "character_name": None,
                "known": [],
                "unknown": [],
            }
        
        character_name = character.name
        
        # Then, get secrets by character name
        result = await db.execute(
            select(Secret).where(Secret.project_id == project_id)
        )
        all_secrets = result.scalars().all()

        known = []
        unknown = []
        for s in all_secrets:
            if character_name in (s.known_by or []):
                known.append(SecretResp.model_validate(s))
            elif character_name in (s.unknown_to or []):
                unknown.append(SecretResp.model_validate(s))

        return {
            "character_id": character_id,
            "character_name": character_name,
            "known": known,
            "unknown": unknown,
        }

    @staticmethod
    async def get_secrets_by_character_name(
        db: AsyncSession,
        project_id: int,
        character_name: str,
    ) -> dict:
        """Get secrets known to and unknown by a specific character (query by name)."""
        # Get all secrets for the project
        result = await db.execute(
            select(Secret).where(Secret.project_id == project_id)
        )
        all_secrets = result.scalars().all()
        
        known = []
        unknown = []
        for s in all_secrets:
            if character_name in (s.known_by or []):
                known.append(SecretResp.model_validate(s))
            elif character_name in (s.unknown_to or []):
                unknown.append(SecretResp.model_validate(s))
        
        return {
            "character_name": character_name,
            "known": known,
            "unknown": unknown,
        }

    @staticmethod
    async def update_secret(
        db: AsyncSession,
        project_id: int,
        secret_id: int,
        data: UpdateSecretReq,
    ) -> SecretResp | None:
        """Update a secret. Returns None if not found or project mismatch."""
        result = await db.execute(
            select(Secret).where(Secret.id == secret_id)
        )
        secret = result.scalar_one_or_none()
        if secret is None or secret.project_id != project_id:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(secret, field):
                setattr(secret, field, value)

        await db.flush()
        await db.refresh(secret)
        return SecretResp.model_validate(secret)

    @staticmethod
    async def update_secrets_by_character(
        db: AsyncSession,
        project_id: int,
        character_id: int,
        data: UpdateSecretsByCharacterReq,
    ) -> dict:
        """Update secrets for a character."""
        # First, get the character name by ID
        result = await db.execute(
            select(VaultCharacter).where(
                VaultCharacter.id == character_id,
                VaultCharacter.project_id == str(project_id),
            )
        )
        character = result.scalar_one_or_none()
        if character is None:
            return {
                "character_id": character_id,
                "character_name": None,
                "updated": [],
                "message": "Character not found",
            }
        
        character_name = character.name
        
        # Then, update or create secrets
        updated_secrets = []
        for item in data.secrets:
            if item.id:
                # Update existing secret
                result = await db.execute(
                    select(Secret).where(Secret.id == item.id)
                )
                secret = result.scalar_one_or_none()
                if secret and secret.project_id == project_id:
                    if item.content:
                        secret.description = item.content
                    if item.secrecy_level:
                        secret.secrecy_level = item.secrecy_level
                    # Update known_by and unknown_to based on related_characters
                    if item.related_characters:
                        # This is a simplified logic - you may need to adjust based on your needs
                        pass
                    await db.flush()
                    await db.refresh(secret)
                    updated_secrets.append(SecretResp.model_validate(secret))
            else:
                # Create new secret
                new_secret = Secret(
                    project_id=project_id,
                    description=item.content or "",
                    known_by=[character_name],
                    unknown_to=[],
                    secrecy_level=item.secrecy_level or "hidden",
                    debt=0,
                )
                db.add(new_secret)
                await db.flush()
                await db.refresh(new_secret)
                updated_secrets.append(SecretResp.model_validate(new_secret))
        
        return {
            "character_id": character_id,
            "character_name": character_name,
            "updated": updated_secrets,
            "message": f"Updated {len(updated_secrets)} secrets",
        }


# Singleton
secret_service = SecretService()
