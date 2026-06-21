"""墨灵 (Moling) — Service 层公用辅助函数。

从 merge_service.py 和 health_monitor.py 抽取的跨文件重复函数。
"""

from __future__ import annotations


def _calc_edit_distance(s1: str, s2: str) -> int:
    """计算两个字符串之间的编辑距离（Levenshtein）。"""
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if not s2:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(
                min(
                    curr_row[j] + 1,         # 删除
                    prev_row[j + 1] + 1,     # 插入
                    prev_row[j] + cost,       # 替换
                )
            )
        prev_row = curr_row
    return prev_row[-1]


def _get_last_advance_chapter(promise) -> int:
    """获取承诺最后推进章节号。

    优先用 advancement_log 最后一条记录的 chapter，
    兜底用 planted_chapter。
    """
    log = promise.advancement_log or []
    if isinstance(log, list) and log:
        last_entry = log[-1]
        if isinstance(last_entry, dict):
            ch = last_entry.get("chapter", 0)
            if ch:
                return ch
    return promise.planted_chapter or 0
