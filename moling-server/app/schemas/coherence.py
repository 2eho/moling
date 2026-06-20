"""墨灵 (Moling) — Coherence Validation Pydantic Schemas.

Defines the structured output contract for the grouped coherence check (Step 10).

Output contract (for frontend consumption via TaskStatusResp.output_data.coherence_check):
{
  "passed": bool,
  "overall_score": float,
  "version": "v2-grouped",
  "groups": [
    {
      "group_name": "narrative_consistency",
      "display_name": "叙事一致性",
      "passed": bool,
      "score": float,
      "checks": [
        { "check_name": "character_consistency", "display_name": "角色行为一致性", "passed": bool, "score": float, "issues": [str] },
        { "check_name": "timeline_continuity",   "display_name": "时间线连续性",   "passed": bool, "score": float, "issues": [str] },
        { "check_name": "plot_promise_status",   "display_name": "伏笔状态",       "passed": bool, "score": float, "issues": [str] }
      ],
      "cross_cutting_issues": [str]
    },
    {
      "group_name": "writing_quality",
      "display_name": "写作质量",
      "passed": bool,
      "score": float,
      "checks": [
        { "check_name": "world_rule_consistency", "display_name": "世界观规则一致性", "passed": bool, "score": float, "issues": [str] },
        { "check_name": "writing_style_consistency", "display_name": "文风一致性", "passed": bool, "score": float, "issues": [str] },
        { "check_name": "narrative_pacing",      "display_name": "叙事节奏",       "passed": bool, "score": float, "issues": [str] },
        { "check_name": "baseline_compliance",   "display_name": "连贯性基线校验",  "passed": bool, "score": float, "issues": [str] }
      ],
      "cross_cutting_issues": [str]
    },
    {
      "group_name": "continuity",
      "display_name": "连续性",
      "passed": bool,
      "score": float,
      "checks": [
        { "check_name": "chapter_transition", "display_name": "章节衔接", "passed": bool, "score": float, "issues": [str] },
        { "check_name": "secret_debt",        "display_name": "秘密债务",  "passed": bool, "score": float, "issues": [str] }
      ],
      "cross_cutting_issues": [str]
    }
  ]
}
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CoherenceCheckItem(BaseModel):
    """A single coherence check result within a group."""

    check_name: str = Field(
        ..., description="检查项标识符（英文蛇形）"
    )
    display_name: str = Field(
        default="", description="检查项中文显示名"
    )
    passed: bool = Field(
        default=True, description="是否通过"
    )
    score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="评分 (0.0–1.0)"
    )
    issues: list[str] = Field(
        default_factory=list, description="问题列表（如有）"
    )


class CoherenceGroupCheck(BaseModel):
    """A grouped coherence check (one LLM call)."""

    group_name: str = Field(
        ..., description="分组标识符（英文蛇形）"
    )
    display_name: str = Field(
        default="", description="分组中文显示名"
    )
    passed: bool = Field(
        default=True, description="该组是否通过"
    )
    score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="该组综合评分 (0.0–1.0)"
    )
    checks: list[CoherenceCheckItem] = Field(
        default_factory=list, description="组内各单项检查结果"
    )
    cross_cutting_issues: list[str] = Field(
        default_factory=list, description="跨维度问题（合并检查才有的发现）"
    )


class CoherenceValidationResult(BaseModel):
    """Top-level result returned by CoherenceService.validate_post_generation()."""

    passed: bool = Field(
        default=True, description="全部检查是否通过"
    )
    overall_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="综合评分 (0.0–1.0)"
    )
    version: str = Field(
        default="v2-grouped", description="检查版本标识"
    )
    groups: list[CoherenceGroupCheck] = Field(
        default_factory=list, description="3 组分组检查结果"
    )

    def flatten_issues(self) -> list[str]:
        """Flatten all failed issues across all groups into a single list.
        
        Used by generation_service to feed _adjust_content.
        """
        issues: list[str] = []
        for group in self.groups:
            if not group.passed:
                for check in group.checks:
                    if not check.passed:
                        issues.extend(check.issues)
                issues.extend(group.cross_cutting_issues)
        return issues


class CoherencePipelineResult(BaseModel):
    """Simplified format stored in task.output_data.coherence_check.
    
    This is what frontend sees in TaskStatusResp.output_data.coherence_check.
    Keeps passed/score at top level for backward compatibility,
    adds version field so frontend can detect v2 format,
    and includes full groups detail for rich UI display.
    """

    passed: bool = Field(
        default=True, description="全部检查是否通过"
    )
    score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="综合评分 (0.0–1.0)"
    )
    version: str = Field(
        default="v2-grouped", description="检查版本标识 — v2-grouped = 3组 合并检测"
    )
    issues: list[str] = Field(
        default_factory=list, description="展平的失败问题列表（用于调整）"
    )
    groups: list[CoherenceGroupCheck] = Field(
        default_factory=list, description="完整分组详情（供前端展示）"
    )


# Group definition constants (shared between service and frontend)
GROUP_DEFINITIONS: list[dict[str, str]] = [
    {
        "group_name": "narrative_consistency",
        "display_name": "叙事一致性",
        "checks": ["character_consistency", "timeline_continuity", "plot_promise_status"],
    },
    {
        "group_name": "writing_quality",
        "display_name": "写作质量",
        "checks": ["world_rule_consistency", "writing_style_consistency", "narrative_pacing", "baseline_compliance"],
    },
    {
        "group_name": "continuity",
        "display_name": "连续性",
        "checks": ["chapter_transition", "secret_debt"],
    },
]
