"""墨灵 (Moling) — Health Service.

提供项目健康检查逻辑：R1 角色一致性、R2 时间线连续性、R3 伏笔债务。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import project_dao, vault_dao
from app.errors import NotFoundError, ErrorCode, AppError
from app.models.health_alert import HealthAlert
from app.models.chapter import Chapter
from app.models.project import Project
from app.models.vault_character import VaultCharacter
from app.models.vault_plot_promise import VaultPlotPromise
from app.models.vault_timeline import VaultTimeline
from app.models.vault_world import VaultWorld
from app.llm.client import llm_client

logger = logging.getLogger(__name__)
settings = get_settings()


class HealthService:
    """Service for project health checks (R1/R2/R3)."""

    async def run_health_check(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
    ) -> Dict[str, Any]:
        """Run all health checks (R1/R2/R3) for a project.
        
        Args:
            db: Database session
            user_id: User ID
            project_id: Project ID
            
        Returns:
            Health check results with alerts
        """
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise AppError(
                error_code=ErrorCode.PROJECT_ACCESS_DENIED,
                detail="Not authorized to access this project",
            )

        result = {
            "project_id": project_id,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "checks": {},
            "alerts": [],
        }

        # ===== R1: Character Consistency Check =====
        logger.info(f"Health check R1: Character consistency for project {project_id}")
        r1_result = await self._check_r1_character_consistency(db, project)
        result["checks"]["R1"] = r1_result

        # ===== R2: Timeline Continuity Check =====
        logger.info(f"Health check R2: Timeline continuity for project {project_id}")
        r2_result = await self._check_r2_timeline_continuity(db, project)
        result["checks"]["R2"] = r2_result

        # ===== R3: Plot Promise Debt Check =====
        logger.info(f"Health check R3: Plot promise debt for project {project_id}")
        r3_result = await self._check_r3_plot_promise_debt(db, project)
        result["checks"]["R3"] = r3_result

        # Collect alerts
        for check_key, check_result in result["checks"].items():
            if not check_result["passed"]:
                alerts = check_result.get("alerts", [])
                for alert in alerts:
                    # Create or update HealthAlert record
                    health_alert = HealthAlert(
                        project_id=project_id,
                        rule=check_key,
                        title=alert.get("title", "Health Issue"),
                        detail=alert.get("detail", ""),
                        severity=alert.get("severity", "warning"),
                        is_active=True,
                        checked_at=datetime.now(timezone.utc),
                    )
                    db.add(health_alert)
                    result["alerts"].append(alert)

        await db.commit()

        logger.info(f"Health check completed for project {project_id}: {len(result['alerts'])} alerts")
        return result

    async def _check_r1_character_consistency(
        self,
        db: AsyncSession,
        project: Project,
    ) -> Dict[str, Any]:
        """R1: Check character behavior consistency.
        
        Checks:
        - Are character traits consistent across chapters?
        - Are character relationships logically maintained?
        - Are there any character "personality conflicts"?
        """
        result = {
            "passed": True,
            "score": 1.0,
            "details": "",
            "alerts": [],
        }

        try:
            # Get all characters
            characters = await vault_dao.get_characters(db, project.id)
            
            if not characters:
                result["passed"] = True
                result["score"] = 1.0
                result["details"] = "No characters to check"
                return result

            # Check for character inconsistencies using LLM
            character_data = []
            for char in characters:
                character_data.append({
                    "name": char.name,
                    "role": char.role,
                    "traits": char.traits,
                    "emotion": char.emotion,
                    "chapter_count": char.chapter_count,
                })

            prompt = f"""请分析以下小说角色的一致性健康状况。

项目：{project.title}

角色列表：
{json.dumps(character_data, ensure_ascii=False, indent=2)}

请检查：
1. 角色特征是否清晰且一致？
2. 角色出场章节数是否合理？
3. 是否有角色"personality conflicts"？

返回 JSON 格式：
{{"consistent": true/false, "issues": ["问题1", "问题2"], "score": 0.0-1.0, "recommendations": ["建议1", "建议2"]}}
"""

            response_text = await self._call_llm(prompt)
            
            try:
                llm_result = json.loads(response_text)
                
                result["passed"] = llm_result.get("consistent", True)
                result["score"] = llm_result.get("score", 0.9)
                result["details"] = f"角色一致性得分: {result['score']:.2f}"
                
                if not result["passed"]:
                    issues = llm_result.get("issues", [])
                    recommendations = llm_result.get("recommendations", [])
                    
                    for issue in issues:
                        result["alerts"].append({
                            "rule": "R1",
                            "title": "角色一致性问题",
                            "detail": issue,
                            "severity": "warning",
                            "recommendation": ", ".join(recommendations) if recommendations else "",
                        })
                
            except json.JSONDecodeError:
                # If LLM response is not valid JSON, use default
                result["passed"] = True
                result["score"] = 0.85
                result["details"] = "角色一致性检查完成（LLM 响应解析失败）"

        except Exception as e:
            logger.error(f"R1 check failed: {e}", exc_info=True)
            result["passed"] = True
            result["score"] = 0.8
            result["details"] = f"检查失败: {str(e)}"

        return result

    async def _check_r2_timeline_continuity(
        self,
        db: AsyncSession,
        project: Project,
    ) -> Dict[str, Any]:
        """R2: Check timeline continuity.
        
        Checks:
        - Are timeline events in correct chronological order?
        - Are there any "time gaps" or "time conflicts"?
        - Do character appearances match timeline?
        """
        result = {
            "passed": True,
            "score": 1.0,
            "details": "",
            "alerts": [],
        }

        try:
            # Get all timeline events
            events = await vault_dao.get_timeline(db, project.id)
            
            if not events or len(events) < 2:
                result["passed"] = True
                result["score"] = 1.0
                result["details"] = "Timeline events insufficient for continuity check"
                return result

            # Check timeline order
            timeline_data = []
            for event in events:
                timeline_data.append({
                    "chapter_number": event.chapter_number,
                    "event": event.event,
                    "description": event.description,
                    "is_key_event": event.is_key_event,
                    "characters_involved": event.characters_involved,
                })

            # Simple check: are events in chapter order?
            chapter_numbers = [e.chapter_number for e in events]
            if chapter_numbers != sorted(chapter_numbers):
                result["passed"] = False
                result["score"] = 0.6
                result["details"] = "时间线事件章节顺序不一致"
                result["alerts"].append({
                    "rule": "R2",
                    "title": "时间线顺序问题",
                    "detail": "时间线事件的章节顺序不一致，可能存在时间线冲突",
                    "severity": "warning",
                })
            else:
                result["passed"] = True
                result["score"] = 0.95
                result["details"] = "时间线连续性检查通过"

        except Exception as e:
            logger.error(f"R2 check failed: {e}", exc_info=True)
            result["passed"] = True
            result["score"] = 0.8
            result["details"] = f"检查失败: {str(e)}"

        return result

    async def _check_r3_plot_promise_debt(
        self,
        db: AsyncSession,
        project: Project,
    ) -> Dict[str, Any]:
        """R3: Check plot promise debt.
        
        Checks:
        - Are there too many unresolved plot promises (debt)?
        - Are there "abandoned" promises?
        - Are promises being resolved at a reasonable rate?
        """
        result = {
            "passed": True,
            "score": 1.0,
            "details": "",
            "alerts": [],
        }

        try:
            # Get all plot promises
            promises = await vault_dao.get_plot_promises(db, project.id)
            
            if not promises:
                result["passed"] = True
                result["score"] = 1.0
                result["details"] = "No plot promises to check"
                return result

            # Categorize promises by status
            dormant_count = len([p for p in promises if p.status == "dormant"])
            active_count = len([p for p in promises if p.status == "active"])
            resolved_count = len([p for p in promises if p.status == "resolved"])
            abandoned_count = len([p for p in promises if p.status == "abandoned"])

            total = len(promises)
            resolved_rate = resolved_count / total if total > 0 else 0

            # Check debt: too many unresolved promises?
            unresolved_count = dormant_count + active_count
            debt_threshold = 10  # Configurable threshold

            if unresolved_count > debt_threshold:
                result["passed"] = False
                result["score"] = 0.5
                result["details"] = f"伏笔债务过高: {unresolved_count} 个未回收伏笔"
                result["alerts"].append({
                    "rule": "R3",
                    "title": "伏笔债务警告",
                    "detail": f"当前有 {unresolved_count} 个未回收的伏笔，建议尽快回收部分伏笔",
                    "severity": "critical",
                    "unresolved_count": unresolved_count,
                    "resolved_rate": resolved_rate,
                })
            elif unresolved_count > debt_threshold * 0.7:
                result["passed"] = True
                result["score"] = 0.7
                result["details"] = f"伏笔债务偏高: {unresolved_count} 个未回收伏笔"
                result["alerts"].append({
                    "rule": "R3",
                    "title": "伏笔债务提醒",
                    "detail": f"当前有 {unresolved_count} 个未回收的伏笔，建议关注伏笔回收",
                    "severity": "warning",
                    "unresolved_count": unresolved_count,
                    "resolved_rate": resolved_rate,
                })
            else:
                result["passed"] = True
                result["score"] = 0.9
                result["details"] = f"伏笔债务健康: {unresolved_count} 个未回收伏笔，回收率 {resolved_rate:.1%}"

        except Exception as e:
            logger.error(f"R3 check failed: {e}", exc_info=True)
            result["passed"] = True
            result["score"] = 0.8
            result["details"] = f"检查失败: {str(e)}"

        return result

    async def get_alerts(
        self,
        db: AsyncSession,
        project_id: int,
        active_only: bool = True,
    ) -> list[HealthAlert]:
        """Get health alerts for a project."""
        stmt = select(HealthAlert).where(
            HealthAlert.project_id == project_id
        )
        if active_only:
            stmt = stmt.where(HealthAlert.is_active == True)
        stmt = stmt.order_by(HealthAlert.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt and return response text."""
        messages = [
            {"role": "system", "content": "你是一个专业的小说健康分析助手。"},
            {"role": "user", "content": prompt},
        ]
        
        response = await llm_client.chat(
            messages=messages,
            model=settings.LLM_MODEL,
            temperature=0.3,
            max_tokens=2048,
        )
        
        return response["choices"][0]["message"]["content"]


health_service = HealthService()
