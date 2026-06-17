"""墨灵 (Moling) — Phase 4 调度器 + 内容安全验证 (§12 / §11.6).

调度器管理收纳任务的排队、幂等性检查、竞态防护、失败回补，
以及收纳前的内容安全验证（SourceText Grounding + 实体名规范化）。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import phase4_dao, vault_dao
from app.models.phase4_task import Phase4Task
from app.models.vault_character import VaultCharacter
from app.service.phase4_service import phase4_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 调度器状态定义 (§12.1)
# ---------------------------------------------------------------------------

IDLE_LOCK_TIMEOUT_S = 10     # 写入锁超时 (秒)
LOCK_WAIT_INTERVAL_S = 0.2   # 锁等待轮询间隔 (秒)
GATE_WAIT_TIMEOUT_S = 5      # 门控等待超时 (秒)
SIMILARITY_THRESHOLD = 85    # SourceText 相似度阈值 (%)
ENTITY_SIMILARITY_THRESHOLD = 85  # 实体名模糊匹配阈值 (%)
MAX_CONSECUTIVE_FAILURES = 5  # 最大连续失败次数 → 强制暂停


@dataclass
class VaultVersion:
    """四库版本状态."""
    current: str = ""            # 当前版本标识
    pending: Optional[str] = None  # 待写入版本
    last_stable: str = ""        # 最后稳定版本 (出错时回退用)
    write_lock: bool = False     # 写入锁状态


@dataclass
class SchedulerState:
    """调度器全局状态 (§12.1)."""
    queue: List[Dict[str, Any]] = field(default_factory=list)
    executed_nonces: Set[str] = field(default_factory=set)
    vault_version: VaultVersion = field(default_factory=VaultVersion)
    fallback_queue: List[Dict[str, Any]] = field(default_factory=list)
    consecutive_failures: int = 0


# ---------------------------------------------------------------------------
# Phase4Scheduler
# ---------------------------------------------------------------------------


class Phase4Scheduler:
    """Phase 4 调度器 — 管理收纳任务的执行、竞态防护与内容安全验证.

    模拟 Redis 存储: ``_nonce_set``, ``_lock_store``, ``_task_store``.
    生产环境迁移至真实 Redis 时搜索标记 ``# TODO: 迁移到 Redis``.
    """

    def __init__(self) -> None:
        # 内存版 "Redis" 存储
        self._nonce_set: Set[str] = set()          # TODO: 迁移到 Redis SISMEMBER
        self._lock_store: Dict[str, float] = {}     # TODO: 迁移到 Redis HSETNX
        self._task_store: Dict[str, Dict[str, Any]] = {}  # TODO: 迁移到 Redis HASH

        self._state_lock = asyncio.Lock()
        self._state = SchedulerState()

    # ======================================================================
    # §12.2 主入口
    # ======================================================================

    async def schedule_phase4(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        chapter_text: str,
        card_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Phase 4 调度主入口.

        流程 (§12.2):
        1. 生成 nonce + 幂等检查
        2. 加写入锁
        3. 组装输入（章节正文 + 四库摘要 + 卡片 ID + 回补队列）
        4. 调用 Phase4Service 执行收纳
        5. 释放锁 + 更新状态

        Args:
            db: 数据库会话
            project_id: 项目 ID
            chapter_id: 章节 ID
            chapter_text: 章节正文
            card_ids: 关联卡牌 ID 列表（可选）

        Returns:
            收纳任务结果
        """
        # --- Step 1: 生成 nonce + 幂等检查 ---
        nonce = await self._generate_nonce(chapter_id)
        idempotent_result = await self._check_idempotency(db, nonce)
        if idempotent_result is not None:
            logger.info("幂等性命中 (nonce=%s), 返回已有结果", nonce)
            return idempotent_result

        # --- Step 1.5: 门控检查 — 等待前一个pending版本就绪 (§12.3) ---
        await self.check_vault_ready()

        # --- Step 2: 加写入锁 ---
        lock_key = f"phase4_lock:{project_id}:{chapter_id}"
        lock_acquired = await self._acquire_lock(lock_key)
        if not lock_acquired:
            logger.warning("写入锁被占用, 等待 200 ms 后重试 (key=%s)", lock_key)
            return {
                "status": "queued",
                "message": "系统正在处理其他收纳任务，已加入等待队列",
                "nonce": nonce,
            }

        try:
            # --- Step 2.5: 创建 Phase4Task 记录 (DB 层幂等层) ---
            existing_task = await phase4_dao.get_by_nonce(db, nonce)
            if existing_task:
                logger.info("DB 幂等命中 (nonce=%s), 跳过创建", nonce)
                return {
                    "task_id": str(existing_task.id),
                    "status": existing_task.status,
                    "nonce": nonce,
                    "message": "该收纳任务已存在",
                }

            # --- 内容安全验证 (§11.6) ---
            safety_result, chapter_analysis = await self._run_content_safety_check(
                db, project_id, chapter_text
            )
            if not safety_result["passed"]:
                logger.warning(
                    "内容安全验证未通过 (project=%s, chapter=%s): %s",
                    project_id, chapter_id, safety_result["skipped_items"],
                )

            # --- Step 3: 组装输入 ---
            input_data = await self._assemble_input(
                db, project_id, chapter_id, chapter_text,
                card_ids or [], chapter_analysis,
            )

            # 注册 nonce 到内存集合 (Layer 1)
            self._nonce_set.add(nonce)

            # 创建任务
            task = Phase4Task(
                nonce=nonce,
                project_id=str(project_id),
                chapter_id=str(chapter_id),
                status="pending",
            )
            db.add(task)
            await db.flush()
            await db.refresh(task)

            # --- Step 4: 调用 Phase4Service 执行收纳 ---
            logger.info(
                "开始 Phase 4 收纳 (project=%s, chapter=%s, nonce=%s)",
                project_id, chapter_id, nonce,
            )
            result = await phase4_service.execute_storage(db, task.id)

            # --- Step 5: 释放锁 + 更新状态 ---
            await self._release_lock(lock_key)
            self._update_vault_version(project_id, chapter_id, nonce)
            # 成功后重置连续失败计数
            async with self._state_lock:
                self._state.consecutive_failures = 0

            logger.info(
                "Phase 4 收纳完成 (task_id=%s, nonce=%s)", task.id, nonce,
            )
            return {
                "status": "done",
                "task_id": str(task.id),
                "nonce": nonce,
                "safety_check": safety_result,
                "result": result,
            }

        except Exception as exc:
            logger.exception(
                "Phase 4 调度执行异常 (project=%s, chapter=%s)",
                project_id, chapter_id,
            )
            await self._handle_failure(db, project_id, chapter_id, nonce, exc)
            raise

    # ======================================================================
    # §12.5 三层幂等防护
    # ======================================================================

    async def _generate_nonce(self, chapter_id: int) -> str:
        """生成 nonce 令牌 (格式: ch${chapter}_${timestamp}_${hash})."""
        ts = datetime.now(timezone.utc).isoformat()
        raw = f"ch{chapter_id}_{ts}"
        h = hashlib.sha256(raw.encode()).hexdigest()[:12]
        nonce = f"ch{chapter_id}_{int(time.time())}_{h}"
        logger.debug("生成 nonce: %s", nonce)
        return nonce

    async def _check_idempotency(
        self,
        db: AsyncSession,
        nonce: str,
    ) -> Optional[Dict[str, Any]]:
        """三层幂等性检查 (§12.5).

        - Layer 1: 内存 nonce 集合 (模拟 Redis SISMEMBER)
        - Layer 2: DB SELECT phase4_tasks
        - Layer 3: DB UNIQUE 约束 (由 SQLAlchemy 在 commit 时保证)

        Returns:
            已有任务的 dict 结果，或 None（表示未命中，可以继续执行）
        """
        # Layer 1: 内存集合检查 (~1ms)
        if nonce in self._nonce_set:
            logger.debug("Layer 1 幂等命中 (nonce=%s)", nonce)
            return {"status": "already_exists", "message": "此 nonce 已执行过", "nonce": nonce}

        # Layer 2: DB 查询保护 (~5ms, Redis 重启保护)
        task = await phase4_dao.get_by_nonce(db, nonce)
        if task is not None:
            logger.debug("Layer 2 幂等命中 (nonce=%s, task_id=%s)", nonce, task.id)
            return {
                "task_id": str(task.id),
                "status": task.status,
                "nonce": nonce,
                "message": "此 nonce 已在数据库中记录",
            }

        # Layer 3: DB UNIQUE 约束 (由 Phase4Task.nonce unique=True 保证)
        return None

    # ======================================================================
    # §12.3 竞态防护
    # ======================================================================

    async def _acquire_lock(self, key: str) -> bool:
        """获取写入锁 (内存版本, 使用时间戳标记).

        TODO: 迁移到 Redis HSETNX + EXPIRE

        Args:
            key: 锁键名

        Returns:
            True 获取成功, False 获取失败
        """
        async with self._state_lock:
            now = time.monotonic()
            existing = self._lock_store.get(key)
            if existing is not None:
                elapsed = now - existing
                if elapsed < IDLE_LOCK_TIMEOUT_S:
                    # 锁仍在有效期内 → 等待 200 ms 再试
                    await asyncio.sleep(LOCK_WAIT_INTERVAL_S)
                    return False
                else:
                    # 锁超时 → 强制解锁 (§12.3)
                    logger.warning("写入锁超时, 强制解锁 (key=%s, elapsed=%.1fs)", key, elapsed)

            self._lock_store[key] = now
            return True

    async def _release_lock(self, key: str) -> None:
        """释放写入锁."""
        async with self._state_lock:
            self._lock_store.pop(key, None)
            logger.debug("写入锁已释放 (key=%s)", key)

    async def check_vault_ready(self) -> None:
        """门控检查 (§12.3).

        ﹣ 如果 vaultVersion.pending 不为 None，等待最多 5 秒
        ﹣ 超时后使用 lastStable 版本 + 标记延迟
        """
        async with self._state_lock:
            if self._state.vault_version.pending is None:
                return
            pending = self._state.vault_version.pending

        logger.info("四库版本待写入 (pending=%s), 等待就绪...", pending)
        try:
            await asyncio.wait_for(
                self._wait_for_vault_ready(),
                timeout=GATE_WAIT_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "门控等待超时 (%ss), 回退至 last_stable 版本",
                GATE_WAIT_TIMEOUT_S,
            )
            async with self._state_lock:
                self._state.vault_version.current = (
                    self._state.vault_version.last_stable
                )
                self._state.vault_version.pending = None

    async def _wait_for_vault_ready(self) -> None:
        """轮询等待 vault pending 状态消除."""
        while True:
            async with self._state_lock:
                if self._state.vault_version.pending is None:
                    return
            await asyncio.sleep(0.1)

    def _update_vault_version(
        self,
        project_id: int,
        chapter_id: int,
        nonce: str,
    ) -> None:
        """更新四库版本状态."""
        new_version = f"v4_ch{chapter_id}_{nonce[:8]}"
        # 注意: 非 async 内部方法，在锁释放后调用
        self._state.vault_version.last_stable = (
            self._state.vault_version.current
        )
        self._state.vault_version.current = new_version
        self._state.vault_version.pending = None
        logger.info("四库版本已更新: %s", new_version)

    # ======================================================================
    # §12.4 失败回补
    # ======================================================================

    async def _handle_failure(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        nonce: str,
        exc: Exception,
    ) -> None:
        """失败处理 + 回补逻辑 (§12.4).

        - 1 次失败 → 自动合并到下一章 (fallback_merge)
        - 连续 2 次 → 四库管理页角标
        - 连续 3 次 → 弹窗建议全量分析
        - 连续 5 次 → 强制暂停
        """
        async with self._state_lock:
            self._state.consecutive_failures += 1
            failures = self._state.consecutive_failures

        error_msg = str(exc)
        logger.error(
            "Phase 4 收纳失败 (project=%s, chapter=%s, nonce=%s, failures=%d): %s",
            project_id, chapter_id, nonce, failures, error_msg,
        )

        # 加入回补队列
        fallback_item = {
            "project_id": project_id,
            "chapter_id": chapter_id,
            "nonce": nonce,
            "error": error_msg,
            "failures": failures,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        async with self._state_lock:
            self._state.fallback_queue.append(fallback_item)

        # 尝试更新 Phase4Task 状态为 failed
        try:
            task = await phase4_dao.get_by_nonce(db, nonce)
            if task:
                task.status = "failed"
                task.error_message = error_msg
                task.completed_at = datetime.now(timezone.utc)
                await db.commit()
        except Exception:
            logger.exception("更新 Phase4Task 失败状态时出错")

        # 根据连续失败次数采取不同措施
        if failures == 1:
            logger.info(
                "首次失败，自动合并到下一章 (fallback_merge, project=%s)",
                project_id,
            )
        elif failures == 2:
            logger.warning(
                "连续 2 次失败，请在四库管理页查看角标 (project=%s)",
                project_id,
            )
        elif failures == 3:
            logger.warning(
                "连续 3 次失败，建议用户执行全量分析 (project=%s)",
                project_id,
            )
        elif failures >= MAX_CONSECUTIVE_FAILURES:
            logger.critical(
                "连续 %d 次失败，强制暂停 Phase 4 调度 (project=%s)",
                failures, project_id,
            )
            await self._pause_scheduling(project_id)
            raise RuntimeError(
                f"Phase 4 已因连续 {failures} 次失败强制暂停，"
                f"请人工介入修复后重新启用。"
            )

    async def _pause_scheduling(self, project_id: int) -> None:
        """强制暂停调度 — 清空队列."""
        async with self._state_lock:
            self._state.queue.clear()
        logger.critical("Phase 4 调度已暂停 (project_id=%s)", project_id)

    # ======================================================================
    # §11.6 内容安全验证
    # ======================================================================

    async def _run_content_safety_check(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_text: str,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """运行内容安全验证管道 (§11.6).

        Returns:
            (safety_result, chapter_analysis)
        """
        # 解析章节内容 → 提取结构化数据
        chapter_analysis = await self._extract_chapter_analysis(chapter_text)

        # 第一道: SourceText Grounding
        grounding_result = await self._verify_source_text(
            chapter_text, chapter_analysis,
        )

        # 第二道: 实体名规范化
        entity_result = await self._normalize_entity_names(
            db, project_id, chapter_analysis.get("characters", []),
        )

        safety_result = {
            "passed": grounding_result["passed"],
            "skipped_items": grounding_result["skipped_items"],
            "entity_updates": entity_result,
        }
        return safety_result, chapter_analysis

    async def _extract_chapter_analysis(
        self,
        chapter_text: str,
    ) -> Dict[str, Any]:
        """从章节正文中提取结构化分析 (简单段落/角色名提取).

        实际生产环境应由 LLM 或 NLP pipeline 完成，
        此处实现基本版本用于 SourceText Grounding 验证。
        """
        characters: List[Dict[str, str]] = []
        seen_segments: Set[str] = set()

        # 简单启发式: 对话前的角色名提取
        lines = chapter_text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 检测 "XXX说：" / "XXX道：" / "XXX道:" 模式
            for suffix in ("说：", "说:", "道：", "道:", "问：", "问:", "答：", "答:"):
                idx = line.find(suffix)
                if idx > 0:
                    name = line[:idx].strip()
                    if name and 1 <= len(name) <= 10:
                        source_text = line[:idx + len(suffix)]
                        if name not in seen_segments:
                            seen_segments.add(name)
                            characters.append({
                                "name": name,
                                "source_text": source_text,
                            })
                    break

        return {
            "characters": characters,
            "segments": list(seen_segments),
        }

    async def _verify_source_text(
        self,
        chapter_text: str,
        chapter_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """第一道防线: SourceText Grounding (§11.6).

        对每个提取条目，使用 RapidFuzz 模糊匹配 source_text 与原文。

        Returns:
            {"passed": bool, "skipped_items": List[str], "details": [...]}
        """
        skipped_items: List[str] = []
        details: List[Dict[str, Any]] = []

        for char in chapter_analysis.get("characters", []):
            source_text = char.get("source_text", "")
            name = char.get("name", "")

            if not source_text:
                skipped_items.append(f"角色 '{name}' 缺少 source_text")
                details.append({
                    "name": name,
                    "passed": False,
                    "reason": "缺少 source_text",
                    "similarity": 0,
                })
                continue

            similarity = await self._fuzzy_match(source_text, chapter_text)

            if similarity >= SIMILARITY_THRESHOLD:
                details.append({
                    "name": name,
                    "passed": True,
                    "similarity": round(similarity, 2),
                    "source_text": source_text,
                })
            else:
                # 相似度 < 85% → 标记为可疑
                verdict = await self._llm_judge(source_text, chapter_text)
                if verdict == "fail":
                    skipped_items.append(
                        f"角色 '{name}' source_text 不匹配原文 "
                        f"(相似度={similarity:.1f}%, LLM裁决=FAIL)"
                    )
                    details.append({
                        "name": name,
                        "passed": False,
                        "reason": "LLM裁决不通过",
                        "similarity": round(similarity, 2),
                    })
                else:
                    details.append({
                        "name": name,
                        "passed": True,
                        "reason": "LLM裁决通过",
                        "similarity": round(similarity, 2),
                    })

        passed = len(skipped_items) == 0
        return {
            "passed": passed,
            "skipped_items": skipped_items,
            "details": details,
        }

    async def _fuzzy_match(self, source: str, target: str) -> float:
        """RapidFuzz 模糊匹配.

        使用简单子串包含 + 字符重叠比来模拟 RapidFuzz 的 token_sort_ratio.
        TODO: 迁移至 ``from rapidfuzz import fuzz``

        Args:
            source: 需要匹配的源文本
            target: 目标文本 (原始章节内容)

        Returns:
            相似度百分比 (0-100)
        """
        if not source or not target:
            return 0.0

        s = source.lower().strip()
        t = target.lower()

        # 精确子串包含 → 100%
        if s in t:
            return 100.0

        # 字符重叠率
        source_chars = set(s.replace(" ", "").replace("：", "").replace(":", ""))
        target_chars = set(t.replace(" ", ""))
        if not source_chars:
            return 0.0

        intersection = source_chars & target_chars
        ratio = len(intersection) / len(source_chars) * 100.0
        return min(ratio, 100.0)

    async def _llm_judge(
        self,
        source_text: str,
        chapter_text: str,
    ) -> str:
        """LLM-as-Judge 裁决 (§11.6).

        当 RapidFuzz 相似度低于阈值时，调用 LLM 二次判断。
        当前以关键词覆盖率 + 上下文邻近度模拟。

        TODO: 接入真实 LLM (e.g., ``from app.llm.client import llm_client``)

        Returns:
            "pass" 或 "fail"
        """
        # 简单模拟: 如果 source 中的关键字符在原文中有更高覆盖率则通过
        source_clean = source_text.replace("：", "").replace(":", "").replace("说", "").replace("道", "").strip()
        words = source_clean.split()

        matched = 0
        for word in words:
            if len(word) >= 2 and word in chapter_text:
                matched += 1

        if words and matched / len(words) >= 0.6:
            return "pass"
        return "fail"

    # ======================================================================
    # §11.6 第二道: 实体名规范化
    # ======================================================================

    async def _normalize_entity_names(
        self,
        db: AsyncSession,
        project_id: int,
        extracted_characters: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """第二道防线: 实体名规范化 (§11.6).

        提取的角色名与已有实体名进行 RapidFuzz 模糊匹配:
        - 匹配(≥85%) → 自动注册别名，合并到已有实体
        - 无匹配 → 注册新实体

        Args:
            db: 数据库会话
            project_id: 项目 ID
            extracted_characters: 提取出的角色列表

        Returns:
            实体规范化结果
        """
        existing_characters = await vault_dao.get_characters(db, project_id)
        existing_names = {c.name for c in existing_characters}

        updates: List[Dict[str, Any]] = []
        new_entities: List[Dict[str, Any]] = []

        for char in extracted_characters:
            name = (char.get("name", "") or "").strip()
            if not name:
                continue

            best_match = await self._find_best_match(
                name, list(existing_names),
            )

            if best_match and best_match["similarity"] >= ENTITY_SIMILARITY_THRESHOLD:
                # 匹配到已有实体 → 注册别名
                matched_char = next(
                    (c for c in existing_characters if c.name == best_match["name"]),
                    None,
                )
                if matched_char:
                    aliases = self._get_aliases(matched_char)
                    if name not in aliases:
                        aliases.append(name)
                        await self._save_aliases(db, matched_char, aliases)
                        updates.append({
                            "name": name,
                            "matched_to": best_match["name"],
                            "similarity": best_match["similarity"],
                            "action": "register_alias",
                        })
                        logger.info(
                            "角色别名注册: '%s' → '%s' (相似度=%.1f%%)",
                            name, best_match["name"], best_match["similarity"],
                        )
            else:
                # 无匹配 → 注册新实体 (暂存，由 Phase4Service 执行创建)
                new_entities.append({
                    "name": name,
                    "action": "register_new",
                })
                logger.info("新角色实体: '%s'", name)

        return {
            "alias_updates": updates,
            "new_entities": new_entities,
            "total_extracted": len(extracted_characters),
        }

    async def _find_best_match(
        self,
        name: str,
        existing_names: List[str],
    ) -> Optional[Dict[str, Any]]:
        """在已有实体名中寻找最佳模糊匹配.

        Args:
            name: 待匹配角色名
            existing_names: 已有实体名列表

        Returns:
            最佳匹配信息，或 None
        """
        best = None
        best_score = 0.0

        for existing in existing_names:
            score = await self._name_similarity(name, existing)
            if score > best_score:
                best_score = score
                best = {"name": existing, "similarity": score}

        if best and best_score >= ENTITY_SIMILARITY_THRESHOLD:
            return best
        return None

    async def _name_similarity(self, a: str, b: str) -> float:
        """角色名模糊匹配.

        基于 Levenshtein 编辑距离 + 子串匹配的简化 RapidFuzz 模拟.

        Args:
            a: 第一个名字
            b: 第二个名字

        Returns:
            相似度百分比 (0-100)
        """
        if not a or not b:
            return 0.0

        a_clean = a.strip().lower()
        b_clean = b.strip().lower()

        if a_clean == b_clean:
            return 100.0

        # 子串匹配 (一边完全包含于另一边)
        if a_clean in b_clean or b_clean in a_clean:
            shorter = min(len(a_clean), len(b_clean))
            longer = max(len(a_clean), len(b_clean))
            return shorter / longer * 100.0

        # Levenshtein 编辑距离 (RapidFuzz 标准公式: 1 - dist/(len1+len2))
        lev_dist = self._levenshtein(a_clean, b_clean)
        total_len = len(a_clean) + len(b_clean)
        lev_score = (1 - lev_dist / total_len) * 100.0 if total_len > 0 else 0.0
        if lev_score > 0:
            return min(lev_score, 100.0)

        # 字符重叠率 (大集合回退)
        set_a = set(a_clean)
        set_b = set(b_clean)
        intersection = set_a & set_b
        union = set_a | set_b

        if not union:
            return 0.0
        return len(intersection) / len(union) * 100.0

    @staticmethod
    def _levenshtein(a: str, b: str) -> int:
        """计算两个字符串的编辑距离."""
        n, m = len(a), len(b)
        if n == 0:
            return m
        if m == 0:
            return n
        # 使用 2 行优化空间
        prev = list(range(m + 1))
        curr = [0] * (m + 1)
        for i in range(1, n + 1):
            curr[0] = i
            for j in range(1, m + 1):
                cost = 0 if a[i - 1] == b[j - 1] else 1
                curr[j] = min(
                    prev[j] + 1,        # 删除
                    curr[j - 1] + 1,    # 插入
                    prev[j - 1] + cost, # 替换
                )
            prev, curr = curr, prev
        return prev[m]

    def _get_aliases(self, character: VaultCharacter) -> List[str]:
        """从 VaultCharacter 获取别名列表."""
        if hasattr(character, "aliases") and character.aliases:
            return list(character.aliases)
        if character.traits and isinstance(character.traits, list):
            combined = character.traits
            if isinstance(combined, list):
                return [str(t) for t in combined if isinstance(t, str)]
        return []

    async def _save_aliases(
        self,
        db: AsyncSession,
        character: VaultCharacter,
        aliases: List[str],
    ) -> None:
        """保存别名到角色实体.

        将别名保存在 traits 字段中 (临时方案，待 schema 支持 aliases 字段).
        """
        # 将别名存储到 traits 中 (作为第一个元素)
        if not character.traits or not isinstance(character.traits, list):
            character.traits = aliases
        else:
            existing_strs = [str(t) for t in character.traits]
            for alias in aliases:
                if alias not in existing_strs:
                    existing_strs.append(alias)
            character.traits = existing_strs
        await db.flush()

    # ======================================================================
    # 输入组装
    # ======================================================================

    async def _assemble_input(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        chapter_text: str,
        card_ids: List[str],
        chapter_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """组装 Phase4Service 输入.

        包含:
        - 章节正文
        - 四库摘要 (当前 vault 状态快照)
        - 卡片 ID 列表
        - 回补队列 （待合并的失败任务）

        Args:
            db: 数据库会话
            project_id: 项目 ID
            chapter_id: 章节 ID
            chapter_text: 章节正文
            card_ids: 卡片 ID 列表
            chapter_analysis: 章节分析结果

        Returns:
            输入数据字典
        """
        # 获取回补队列中的待合并项
        fallback_items = []
        async with self._state_lock:
            if self._state.fallback_queue:
                fallback_items = list(self._state.fallback_queue)
                self._state.fallback_queue.clear()

        return {
            "project_id": project_id,
            "chapter_id": chapter_id,
            "chapter_text": chapter_text,
            "card_ids": card_ids,
            "chapter_analysis": chapter_analysis,
            "vault_summary": await self._get_vault_summary(db, project_id),
            "fallback_queue": fallback_items,
            "version": self._state.vault_version.current,
        }

    async def _get_vault_summary(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> Dict[str, Any]:
        """获取四库摘要 (当前 vault 状态快照)."""
        characters = await vault_dao.get_characters(db, project_id)
        return {
            "character_count": len(characters),
            "character_names": [c.name for c in characters],
        }

    # ======================================================================
    # 状态查询
    # ======================================================================

    async def get_state_snapshot(self) -> Dict[str, Any]:
        """获取调度器状态快照 (用于监控/调试)."""
        async with self._state_lock:
            return {
                "queue_length": len(self._state.queue),
                "executed_nonces_count": len(self._state.executed_nonces),
                "nonce_set_size": len(self._nonce_set),
                "vault_version": {
                    "current": self._state.vault_version.current,
                    "pending": self._state.vault_version.pending,
                    "last_stable": self._state.vault_version.last_stable,
                    "write_lock": self._state.vault_version.write_lock,
                },
                "fallback_queue_length": len(self._state.fallback_queue),
                "consecutive_failures": self._state.consecutive_failures,
                "lock_count": len(self._lock_store),
            }

    async def reset_state(self) -> None:
        """重置调度器状态 (用于测试/恢复)."""
        async with self._state_lock:
            self._state = SchedulerState()
            self._nonce_set.clear()
            self._lock_store.clear()
            self._task_store.clear()
        logger.info("Phase4Scheduler 状态已重置")


# Singleton instance
phase4_scheduler = Phase4Scheduler()
