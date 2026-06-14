"""墨灵 (Moling) — Secret (秘密矩阵) Service Layer.

Implements complete secret matrix lifecycle:
1. Secret creation (extract from generated content)
2. Secret propagation (spread knowledge across characters)
3. Secret exposure (expose when conditions are met)
4. Secret debt model (unexposed secrets accumulate "debt")
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import project_dao, vault_dao
from app.errors import NotFoundError, ErrorCode
from app.models.secret import Secret
from app.models.vault_character import VaultCharacter
from app.schemas.secret import SecretResp, UpdateSecretReq, UpdateSecretsByCharacterReq
from app.llm.client import llm_client

logger = logging.getLogger(__name__)
settings = get_settings()


class SecretService:
    """Business logic for secret matrix operations (full lifecycle)."""

    async def extract_secrets_from_content(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        chapter_content: str,
    ) -> List[Dict[str, Any]]:
        """Extract secrets from generated chapter content using LLM.
        
        Args:
            db: Database session
            project_id: Project ID
            chapter_id: Chapter ID
            chapter_content: Generated chapter content
            
        Returns:
            List of extracted secrets with metadata
        """
        # Get project info
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        
        # Get characters for context
        characters = await vault_dao.get_characters(db, project_id)
        character_names = [c.name for c in characters]
        
        # Build LLM prompt for secret extraction
        prompt = f"""请从以下小说章节内容中提取秘密/隐藏信息。

项目：{project.title}
类型：{project.genre}

章节内容：
{chapter_content}

已知角色：{', '.join(character_names)}

请提取所有秘密信息，包括：
1. 某个角色隐藏的真相
2. 角色之间的信息不对称
3. 未公开的事件或计划
4. 角色的真实意图

返回 JSON 格式：
[
    {{
        "description": "秘密描述",
        "known_by": ["知道该秘密的角色名"],
        "unknown_to": ["不知道该秘密的角色名"],
        "secrecy_level": "hidden/partial/revealed",
        "created_chapter": {chapter_id}
    }},
    ...
]

注意：
- 如果某角色不知道秘密，列入 unknown_to
- 如果所有角色都不知道，known_by 为空数组
- secrecy_level: hidden（完全隐藏）, partial（部分知晓）, revealed（已曝光）
"""

        try:
            messages = [
                {"role": "system", "content": "你是一个专业的小说秘密信息提取助手。"},
                {"role": "user", "content": prompt},
            ]
            
            response = await llm_client.chat(
                messages=messages,
                model=settings.LLM_MODEL,
                temperature=0.3,
                max_tokens=2048,
            )
            
            response_text = response["choices"][0]["message"]["content"]
            
            # Parse JSON response
            try:
                json_start = response_text.find("[")
                json_end = response_text.rfind("]") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    extracted = json.loads(json_str)
                else:
                    extracted = []
            except json.JSONDecodeError:
                extracted = []
            
            # Create Secret records
            created_secrets = []
            for item in extracted:
                secret = Secret(
                    project_id=project_id,
                    description=item.get("description", ""),
                    known_by=item.get("known_by", []),
                    unknown_to=item.get("unknown_to", []),
                    secrecy_level=item.get("secrecy_level", "hidden"),
                    created_chapter=chapter_id,
                    debt=0,
                )
                db.add(secret)
                created_secrets.append(secret)
            
            await db.flush()
            
            logger.info(f"Extracted {len(created_secrets)} secrets from chapter {chapter_id}")
            return [{"id": s.id, "description": s.description} for s in created_secrets]
            
        except Exception as e:
            logger.error(f"Secret extraction failed: {e}", exc_info=True)
            return []

    async def propagate_secret(
        self,
        db: AsyncSession,
        project_id: int,
        secret_id: int,
        new_knower: str,
    ) -> Optional[SecretResp]:
        """Propagate a secret to a new character (knowledge spread).
        
        Args:
            db: Database session
            project_id: Project ID
            secret_id: Secret ID
            new_knower: Name of character who now knows the secret
            
        Returns:
            Updated SecretResp or None
        """
        # Get secret
        stmt = select(Secret).where(
            Secret.id == secret_id,
            Secret.project_id == project_id,
        )
        result = await db.execute(stmt)
        secret = result.scalar_one_or_none()
        
        if secret is None:
            return None
        
        # Add new knower
        known_by = secret.known_by or []
        if new_knower not in known_by:
            known_by.append(new_knower)
            secret.known_by = known_by
        
        # Remove from unknown_to
        unknown_to = secret.unknown_to or []
        if new_knower in unknown_to:
            unknown_to.remove(new_knower)
            secret.unknown_to = unknown_to
        
        # Update secrecy_level if more characters know
        if len(known_by) >= 2:
            secret.secrecy_level = "partial"
        
        await db.flush()
        await db.refresh(secret)
        
        logger.info(f"Propagated secret {secret_id} to {new_knower}")
        return SecretResp.model_validate(secret)

    async def expose_secret(
        self,
        db: AsyncSession,
        project_id: int,
        secret_id: int,
        exposure_chapter: Optional[int] = None,
    ) -> Optional[SecretResp]:
        """Expose a secret (when conditions are met).
        
        Args:
            db: Database session
            project_id: Project ID
            secret_id: Secret ID
            exposure_chapter: Chapter number where secret is exposed
            
        Returns:
            Updated SecretResp or None
        """
        # Get secret
        stmt = select(Secret).where(
            Secret.id == secret_id,
            Secret.project_id == project_id,
        )
        result = await db.execute(stmt)
        secret = result.scalar_one_or_none()
        
        if secret is None:
            return None
        
        # Mark as revealed
        secret.secrecy_level = "revealed"
        
        # Add exposure metadata (you may want to add an exposure_log field to the model)
        # For now, we'll just update the status
        
        await db.flush()
        await db.refresh(secret)
        
        logger.info(f"Exposed secret {secret_id} at chapter {exposure_chapter}")
        return SecretResp.model_validate(secret)

    async def calculate_secret_debt(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> Dict[str, Any]:
        """Calculate secret debt for a project.
        
        Debt accumulates for:
        - Unexposed secrets (secrecy_level = "hidden" or "partial")
        - Secrets that have existed for many chapters without exposure
        
        Args:
            db: Database session
            project_id: Project ID
            
        Returns:
            Debt calculation result
        """
        # Get all secrets for the project
        stmt = select(Secret).where(Secret.project_id == project_id)
        result = await db.execute(stmt)
        secrets = result.scalars().all()
        
        if not secrets:
            return {
                "total_debt": 0,
                "hidden_count": 0,
                "partial_count": 0,
                "revealed_count": 0,
                "details": [],
            }
        
        # Calculate debt
        total_debt = 0
        hidden_count = 0
        partial_count = 0
        revealed_count = 0
        details = []
        
        for secret in secrets:
            if secret.secrecy_level == "hidden":
                hidden_count += 1
                debt = (secret.debt or 0) + 1  # Increase debt
                total_debt += debt
                secret.debt = debt
                
                details.append({
                    "secret_id": secret.id,
                    "description": secret.description,
                    "debt": debt,
                    "status": "hidden",
                })
                
            elif secret.secrecy_level == "partial":
                partial_count += 1
                debt = (secret.debt or 0) + 0.5  # Partial debt
                total_debt += debt
                secret.debt = debt
                
                details.append({
                    "secret_id": secret.id,
                    "description": secret.description,
                    "debt": debt,
                    "status": "partial",
                })
                
            else:  # revealed
                revealed_count += 1
                # Reset debt for revealed secrets
                secret.debt = 0
        
        await db.flush()
        
        result = {
            "total_debt": total_debt,
            "hidden_count": hidden_count,
            "partial_count": partial_count,
            "revealed_count": revealed_count,
            "details": details,
        }
        
        logger.info(f"Calculated secret debt for project {project_id}: {total_debt}")
        return result

    async def update_secret_matrix(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        chapter_content: str,
    ) -> Dict[str, Any]:
        """Update the secret matrix after chapter generation (called by Phase 4).
        
        This method:
        1. Extracts new secrets from the chapter
        2. Propagates existing secrets based on chapter events
        3. Checks for secret exposure conditions
        4. Updates secret debt
        
        Args:
            db: Database session
            project_id: Project ID
            chapter_id: Chapter ID
            chapter_content: Generated chapter content
            
        Returns:
            Update result
        """
        result = {
            "extracted_secrets": [],
            "propagated_secrets": [],
            "exposed_secrets": [],
            "debt": {},
        }
        
        # 1. Extract new secrets
        logger.info(f"Updating secret matrix for chapter {chapter_id}: extracting secrets")
        extracted = await self.extract_secrets_from_content(
            db, project_id, chapter_id, chapter_content
        )
        result["extracted_secrets"] = extracted
        
        # 2. TODO: Propagate existing secrets based on chapter events
        # This requires analyzing the chapter to see which characters interact
        
        # 3. TODO: Check for secret exposure conditions
        # For example, if a character who knows a secret reveals it to others
        
        # 4. Update secret debt
        logger.info(f"Updating secret matrix for chapter {chapter_id}: calculating debt")
        debt = await self.calculate_secret_debt(db, project_id)
        result["debt"] = debt
        
        await db.commit()
        
        logger.info(f"Secret matrix update completed for chapter {chapter_id}")
        return result

    # ===== Existing methods (updated to instance methods) =====

    async def list_secrets(
        self,
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

    async def get_secrets_by_character(
        self,
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

    async def get_secrets_by_character_name(
        self,
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

    async def update_secret(
        self,
        db: AsyncSession,
        project_id: int,
        secret_id: int,
        data: UpdateSecretReq,
    ) -> Optional[SecretResp]:
        """Update a secret. Returns None if not found or project mismatch."""
        stmt = select(Secret).where(Secret.id == secret_id)
        result = await db.execute(stmt)
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

    async def update_secrets_by_character(
        self,
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


# Singleton instance
secret_service = SecretService()
