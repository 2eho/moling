# 墨灵 · 卡牌组合算法补充文档

> 本文档补充 `009_2b7b5b03_moling-card-combination-algorithm.md` 中缺失的详细实现文档。
> 
> **生成时间**：2026-06-14
> **关联文档**：`009_2b7b5b03_moling-card-combination-algorithm.md`（主文档）

---

## 目录

1. [卡牌生命周期管理](#卡牌生命周期管理)
2. [健康监控规则详细实现](#健康监控规则详细实现)
3. [novel_dissector 模块清单](#novel_dissector-模块清单)

---

## 卡牌生命周期管理

> **状态**：✅ 已实现（根据 CHANGELOG-2026-06-13.md）

### 生命周期状态图

```
┌────────────────────────────────┐
│  卡牌创建（抽卡获得）           │
│  status = "fresh"                   │
│  fresh_until = now() + 2章节        │
└────────────┬───────────────────┘
             │
    用户确认章节收纳 │
             ▼
┌────────────────────────────────┐
│  检查新鲜期                         │
│  if now() < fresh_until:           │
│    → 保留在活跃池中                 │
│  else:                            │
│    → 进入退役检查                   │
└────────────┬───────────────────┘
             │
       2章节无使用 │
             ▼
┌────────────────────────────────┐
│  卡牌退役                             │
│  status = "retired"               │
│  retired_at = now()                │
│  → 不再参与抽卡                   │
└────────────┬───────────────────┘
             │
       再 2章节无使用 │
             ▼
┌────────────────────────────────┐
│  卡牌淘汰                             │
│  status = "archived"              │
│  archived_at = now()               │
│  → 软删除，可恢复                   │
└────────────────────────────────┘
```

### 数据库字段

```sql
ALTER TABLE card_pool ADD COLUMN status VARCHAR(20) DEFAULT 'fresh';
ALTER TABLE card_pool ADD COLUMN fresh_until TIMESTAMP;
ALTER TABLE card_pool ADD COLUMN retired_at TIMESTAMP;
ALTER TABLE card_pool ADD COLUMN archived_at TIMESTAMP;
```

### 自动检查触发点

| 触发点 | 检查内容 |
|--------|---------|
| 章节收纳完成 | 检查所有参与卡牌的新鲜期 |
| 抽卡时 | 排除已退役/淘汰的卡牌 |
| 手动操作 | 用户可主动退役卡牌 |

---

## 健康监控规则详细实现

> **状态**：✅ 已实现（根据 CHANGELOG-2026-06-13.md）

### R1：伏笔推进检查

**规则**：每个 `plot_promise` 必须有推进章节，否则触发告警。

**实现逻辑**：

```python
# app/services/health_service.py

def check_r1(project_id: str, current_chapter_number: int) -> list[HealthAlert]:
    alerts = []
    promises = vault_dao.get_all_promises(project_id)
    dynamic_layer = get_latest_dynamic_layer(project_id)
    
    for promise in promises:
        if promise.status != "open":
            continue  # 已解决的伏笔跳过
            
        chapters_since_created = current_chapter_number - promise.created_chapter
        
        if chapters_since_created > 8:
            alerts.append(HealthAlert(
                rule="R1",
                promise_id=promise.id,
                promise_title=promise.title,
                level="yellow" if chapters_since_created < 12 else "red",
                detail=f"伏笔已 {chapters_since_created} 章未推进"
            ))
    
    return alerts
```

**告警级别**：
- `yellow`：8-11 章未推进
- `red`：≥12 章未推进

---

### R2：角色一致性检查

**规则**：角色在最近 3 章中的行为/描述必须一致。

**实现逻辑**：

```python
def check_r2(project_id: str, current_chapter_number: int) -> list[HealthAlert]:
    alerts = []
    characters = vault_dao.get_all_characters(project_id)
    recent_chapters = get_recent_chapters(project_id, n=3)
    
    for character in characters:
        traits_in_vault = set(character.traits.keys())
        traits_in_chapters = set()
        
        for chapter in recent_chapters:
            # LLM 提取章节中该角色的实际表现
            chapter_traits = llm_extract_character_traits(chapter.content, character.name)
            traits_in_chapters.update(chapter_traits)
        
        # 检查一致性
        inconsistent = traits_in_vault - traits_in_chapters
        if len(inconsistent) >= 2:
            alerts.append(HealthAlert(
                rule="R2",
                character_id=character.id,
                character_name=character.name,
                level="yellow",
                detail=f"角色 {character.name} 的最近表现与设定不一致"
            ))
    
    return alerts
```

---

### R3：世界规则遵守检查

**规则**：最近 3 章不得违反已设定的世界规则。

**实现逻辑**：

```python
def check_r3(project_id: str, current_chapter_number: int) -> list[HealthAlert]:
    alerts = []
    world_rules = vault_dao.get_world_rules(project_id)
    recent_chapters = get_recent_chapters(project_id, n=3)
    
    for chapter in recent_chapters:
        # LLM 检查章节内容是否违反世界规则
        violations = llm_check_world_violations(chapter.content, world_rules)
        
        if violations:
            for violation in violations:
                alerts.append(HealthAlert(
                    rule="R3",
                    rule_id=violation.rule_id,
                    rule_description=violation.rule_description,
                    level="red",
                    detail=f"第 {chapter.number} 章违反世界规则：{violation.description}"
                ))
    
    return alerts
```

---

## novel_dissector 模块清单

> **状态**：✅ 已实现

### 核心模块列表

| 模块 | 功能 | 主要 API |
|------|------|----------|
| `cleaner.py` | HTML 清洗、章节内容清洗 | `clean_html()`, `clean_chapter_content()`, `is_chapter_heading()` |
| `fetcher.py` | 数据获取（网页爬取） | `Fetcher`, `AntiCrawlConfig`, `FetchResult` |
| `extractor.py` | 内容提取（从 HTML 提取正文） | `extract_content()`, `ExtractResult` |
| `toc_crawler.py` | 目录爬取（获取章节链接） | `TOCFetcher`, `ChapterBatchCrawler`, `ChapterLink`, `CrawlProgress` |
| `style_analyzer.py` | 文风分析 | `StyleFingerprint`, `analyze_style()`, `analyze_style_from_chapters()` |
| `style_prompt_builder.py` | 文风 Prompt 注入 | `fingerprint_to_prompt()`, `fingerprint_to_compact()` |

### 在拆书引擎中的位置

```
输入: 小说前 3-5 章原文
    ↓
[A1] 黄金三章结构提取
    ↓ 使用 cleaner.py 清洗 → extractor.py 提取正文
[A2] 角色出场模式聚类
    ↓ 使用 fetcher.py 获取多本小说 → extractor.py 提取角色信息
[A3] 钩子密度量化
    ↓ 使用 toc_crawler.py 获取章节结构
[A4] 节奏曲线拟合
    ↓
[A5] 套路归纳 + 去版权
    ↓ 使用 style_analyzer.py 分析文风 → style_prompt_builder.py 生成 Prompt
    ↓
输出: Genre Profile (JSON)
```

---

## 变更记录

| 日期 | 变更内容 | 原因 |
|------|---------|------|
| 2026-06-14 | 创建补充文档 | 主文档缺失卡牌生命周期、健康监控、模块清单的详细实现 |

