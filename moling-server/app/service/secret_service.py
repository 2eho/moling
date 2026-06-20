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
from typing import Optional, Dict, List, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import project_dao, vault_dao, secret_dao
from app.errors import NotFoundError, ErrorCode
from app.models.secret import Secret
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
        secret = await secret_dao.get_by_id(db, secret_id)
        
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
        secret = await secret_dao.get_by_id(db, secret_id)
        
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
        secrets = await secret_dao.list_by_project(db, project_id)
        
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
        
        # 2. 根据章节事件传播现有秘密
        logger.info(f"Updating secret matrix for chapter {chapter_id}: propagating secrets")
        characters = await vault_dao.get_characters(db, project_id)
        propagated = await self._propagate_secrets_from_chapter(
            db, project_id, chapter_id, chapter_content, characters
        )
        result["propagated_secrets"] = propagated
        
        # 3. 检查秘密曝光条件
        logger.info(f"Updating secret matrix for chapter {chapter_id}: checking exposure")
        exposed = await self._check_exposure_from_chapter(
            db, project_id, chapter_id, chapter_content, characters
        )
        result["exposed_secrets"] = exposed
        
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
        secrets = await secret_dao.list_by_project(db, project_id)
        return [SecretResp.model_validate(s) for s in secrets]

    async def get_secrets_by_character(
        self,
        db: AsyncSession,
        project_id: int,
        character_id: int,
    ) -> dict:
        """Get secrets known to and unknown by a specific character."""
        # First, get the character name by ID
        character = await vault_dao.get_character(db, character_id)
        if character is None or character.project_id != project_id:
            return {
                "character_id": character_id,
                "character_name": None,
                "known": [],
                "unknown": [],
            }
        
        character_name = character.name
        
        # Then, get secrets by character name
        all_secrets = await secret_dao.list_by_project(db, project_id)
        
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
        all_secrets = await secret_dao.list_by_project(db, project_id)
        
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
        secret = await secret_dao.get_by_id(db, secret_id)
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
        character = await vault_dao.get_character(db, character_id)
        if character is None or str(character.project_id) != str(project_id):
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
                secret = await secret_dao.get_by_id(db, item.id)
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

    async def _propagate_secrets_from_chapter(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        chapter_content: str,
        characters: list,
    ) -> list[dict]:
        """根据章节内容传播秘密：分析章节中出现的角色互动，将秘密在互动角色间传播。"""
        if not characters or not chapter_content:
            return []

        # 获取本章节所有未曝光秘密
        secrets = await secret_dao.list_by_project(db, project_id)
        all_secrets = [s for s in secrets if s.secrecy_level in ("hidden", "partial")]

        if not all_secrets:
            return []

        character_names = [c.name for c in characters]

        # 使用 LLM 分析章节中哪些角色在互动
        prompt = f"""请分析以下章节内容，列出所有出场角色及其之间的互动关系。

章节内容：
{chapter_content[:2000]}

已知角色：{', '.join(character_names[:30])}

请以 JSON 格式返回角色互动列表（只返回在章节中实际出现的角色）：
[
    {{
        "character": "角色A",
        "interacted_with": ["角色B", "角色C"],
        "interaction_type": "dialogue / observation / conflict / cooperation / alone"
    }}
]

注意：
- 只包含在章节中实际出现且有互动的角色
- 如果角色独自出现没有互动，interacted_with 为空列表
- interaction_type 描述互动类型
- 返回纯 JSON，不包含其他文字"""

        try:
            messages = [
                {"role": "system", "content": "你是一个专门分析角色互动的助手。"},
                {"role": "user", "content": prompt},
            ]
            response = await llm_client.chat(
                messages=messages,
                model=settings.LLM_MODEL,
                temperature=0.2,
                max_tokens=1024,
            )
            content = response["choices"][0]["message"]["content"]
            json_start = content.find("[")
            json_end = content.rfind("]") + 1
            if json_start < 0 or json_end <= json_start:
                return []

            interactions = json.loads(content[json_start:json_end])
        except Exception as e:
            logger.error(f"Character interaction analysis failed: {e}", exc_info=True)
            return []

        # 基于互动关系传播秘密
        propagated = []
        for interaction in interactions:
            char_name = interaction.get("character", "")
            interacted_with = interaction.get("interacted_with", [])

            if not char_name or char_name not in character_names:
                continue

            # 获取该角色知道的秘密
            known_secrets = [s for s in all_secrets if char_name in (s.known_by or [])]

            # 向互动对象传播秘密
            for partner in interacted_with:
                if partner not in character_names:
                    continue
                for secret in known_secrets:
                    if partner not in (secret.known_by or []) and partner not in (secret.unknown_to or []):
                        # 传播秘密
                        known_by = secret.known_by or []
                        known_by.append(partner)
                        secret.known_by = known_by

                        # 更新 unknown_to
                        unknown_to = secret.unknown_to or []
                        if partner in unknown_to:
                            unknown_to.remove(partner)
                            secret.unknown_to = unknown_to

                        # 更新等级
                        if len(known_by) >= 2:
                            secret.secrecy_level = "partial"

                        logger.info(
                            f"Propagated secret {secret.id} from {char_name} to {partner}"
                        )
                        propagated.append({
                            "secret_id": secret.id,
                            "description": secret.description[:50],
                            "from": char_name,
                            "to": partner,
                        })

        await db.flush()
        return propagated

    async def _check_exposure_from_chapter(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        chapter_content: str,
        characters: list,
    ) -> list[dict]:
        """检查章节中是否有秘密被曝光：分析章节内容，判断是否有角色公开了秘密。"""
        if not chapter_content:
            return []

        # 获取所有未曝光但部分知晓的秘密（有人知道但未完全公开）
        partial_secrets = await secret_dao.list_by_secrecy_level(db, project_id, "partial")

        if not partial_secrets:
            return []

        # 使用 LLM 检查是否有秘密被公开
        secrets_desc = "\n".join([
            f"- 秘密{s.id}: {s.description[:100]} (知道者: {', '.join(s.known_by or [])})"
            for s in partial_secrets[:10]
        ])

        prompt = f"""请分析以下章节内容，判断是否有原本隐藏的秘密被角色公开说出。

现有秘密：
{secrets_desc}

章节内容：
{chapter_content[:3000]}

请判断是否有任何秘密在本章中被角色公开。如果有，以 JSON 格式返回被曝光的秘密：
[
    {{
        "secret_id": 秘密ID(数字),
        "description": "秘密描述",
        "exposed_by": "曝光该秘密的角色名",
        "confidence": 0.0-1.0
    }}
]

如果没有秘密被曝光，返回空数组 []。
注意：只返回 JSON，不包含其他文字。"""

        try:
            messages = [
                {"role": "system", "content": "你是一个专门分析秘密曝光的小说分析助手。"},
                {"role": "user", "content": prompt},
            ]
            response = await llm_client.chat(
                messages=messages,
                model=settings.LLM_MODEL,
                temperature=0.2,
                max_tokens=1024,
            )
            content = response["choices"][0]["message"]["content"]
            json_start = content.find("[")
            json_end = content.rfind("]") + 1
            if json_start < 0 or json_end <= json_start:
                return []

            exposed_candidates = json.loads(content[json_start:json_end])
        except Exception as e:
            logger.error(f"Exposure check failed: {e}", exc_info=True)
            return []

        # 标记被曝光的秘密
        exposed = []
        for candidate in exposed_candidates:
            secret_id = candidate.get("secret_id")
            if not secret_id:
                continue

            secret = next((s for s in partial_secrets if s.id == secret_id), None)
            if secret and secret.secrecy_level != "revealed":
                secret.secrecy_level = "revealed"
                logger.info(f"Exposed secret {secret_id} at chapter {chapter_id}")
                exposed.append({
                    "secret_id": secret_id,
                    "description": secret.description[:50],
                    "exposed_by": candidate.get("exposed_by", "unknown"),
                })

        await db.flush()
        return exposed


# Singleton instance
secret_service = SecretService()
