"""
墨灵 (Moling) — Import Service.

负责文件导入和内容分析的业务逻辑：
- 解析上传的书籍文件（txt / docx / epub）
- 按章节标记拆分内容
- 提取元数据（标题、作者等）
- 创建项目并写入章节
- 分析章节结构和文本风格
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import re
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.dao import project_dao, chapter_dao
from app.errors import ErrorCode, NotFoundError, ValidationError
from app.models import Project, Chapter

logger = logging.getLogger(__name__)

settings = get_settings()


# ---------------------------------------------------------------------------
# 辅助：Worker 场景下的数据库会话工厂
# ---------------------------------------------------------------------------

def _get_db_url() -> str:
    """返回适配平台的数据库 URL（Windows + SQLite 用 aiosqlite）."""
    url = settings.DATABASE_URL
    if platform.system() == "Windows" and url.startswith("sqlite"):
        if "aiosqlite" not in url:
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def _create_session_factory() -> async_sessionmaker[AsyncSession]:
    """构建异步 sessionmaker 实例."""
    engine = create_async_engine(_get_db_url(), echo=False, pool_size=2)
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """延迟初始化 session factory（避免模块导入时创建引擎）."""
    global _session_factory
    if _session_factory is None:
        _session_factory = _create_session_factory()
    return _session_factory


# ---------------------------------------------------------------------------
# 章节拆分辅助
# ---------------------------------------------------------------------------

_CHAPTER_PATTERNS: list[re.Pattern] = [
    # 第X章 / 第X节 / 第X回
    re.compile(
        r"^[  \t]*(?:第[零一二三四五六七八九十百千万\d]+[章节回卷部]"
        r"(?:[\s　]*[-—].*)?)[  \t]*$",
        re.MULTILINE,
    ),
    # Chapter X / CHAPTER X
    re.compile(
        r"^[  \t]*(?:Chapter\s+\d+"
        r"(?:[\s　]*[-—].*)?)[  \t]*$",
        re.MULTILINE | re.IGNORECASE,
    ),
    # 数字序号标题: 1. / 1、/ 1）开头
    re.compile(
        r"^[  \t]*(?:\d+[\.\、\)）][ \t]*(?:[^0-9].*))$",
        re.MULTILINE,
    ),
    # 卷一 / 卷二 / 上部 / 下部
    re.compile(
        r"^[  \t]*(?:第[零一二三四五六七八九十百千万\d]+卷|"
        r"[上中下前後][部篇集])[  \t]*$",
        re.MULTILINE,
    ),
]


def _find_chapter_boundaries(text: str) -> list[int]:
    """扫描文本，返回所有章节起始位置（字符索引）.

    结合多组模式扫描，去重排序后返回。
    """
    boundaries: set[int] = set()
    for pattern in _CHAPTER_PATTERNS:
        for match in pattern.finditer(text):
            boundaries.add(match.start())

    if not boundaries:
        return [0]

    return [0] + sorted(boundaries)


def _extract_chapter_title(text: str) -> str | None:
    """从一行文本中提取章节标题."""
    for pattern in _CHAPTER_PATTERNS:
        m = pattern.match(text.strip())
        if m:
            return m.group(0).strip()
    return None


def _split_chapters(text: str) -> list[dict[str, str]]:
    """将文本拆分为章节列表.

    返回: [{"title": "第1章 开篇", "content": "..."}, ...]
    """
    boundaries = _find_chapter_boundaries(text)
    chapters: list[dict[str, str]] = []
    lines = text.split("\n")

    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else len(text)
        chunk = text[start:end].strip()
        if not chunk:
            continue

        # 取第一行作为标题
        first_line_end = chunk.find("\n")
        if first_line_end == -1:
            first_line_end = len(chunk)

        title = chunk[:first_line_end].strip()
        content = chunk[first_line_end:].strip()

        detected_title = _extract_chapter_title(title)
        if detected_title:
            title = detected_title
            # 标题行后是内容
        elif not title:
            title = f"第{len(chapters) + 1}章"

        chapters.append({"title": title, "content": content})

    return chapters


# ---------------------------------------------------------------------------
# 文件解析辅助
# ---------------------------------------------------------------------------

def _parse_txt(file_path: str) -> str:
    """解析纯文本文件，尝试多种编码."""
    encodings = ["utf-8", "gbk", "gb2312", "gb18030", "latin-1"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as fh:
                return fh.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValidationError(
        error_code=ErrorCode.VALIDATION_ERROR,
        detail="无法识别文件编码，请确认文件为 UTF-8 或 GBK 编码",
    )


def _parse_docx(file_path: str) -> str:
    """解析 docx 文件，提取纯文本."""
    try:
        from docx import Document
    except ImportError:
        logger.warning("python-docx 未安装，退回 TXT 解析")
        return _parse_txt(file_path)

    doc = Document(file_path)
    paragraphs = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text)
    return "\n".join(paragraphs)


def _parse_epub(file_path: str) -> str:
    """解析 epub 文件，提取章节文本."""
    try:
        from ebooklib import epub
    except ImportError:
        logger.warning("ebooklib 未安装，退回 TXT 解析")
        return _parse_txt(file_path)

    book = epub.read_epub(file_path)
    items = []
    for item in book.get_items():
        if item.get_type() == 9:  # ITEM_DOCUMENT
            content = item.get_content().decode("utf-8", errors="replace")
            # 简单去除 HTML 标签
            content = re.sub(r"<[^>]+>", "", content)
            content = re.sub(r"\s+", " ", content).strip()
            if content:
                items.append(content)

    if not items:
        raise ValidationError(
            error_code=ErrorCode.VALIDATION_ERROR,
            detail="epub 文件中未找到可读内容",
        )

    return "\n\n".join(items)


def _parse_file(file_path: str) -> str:
    """根据文件扩展名选择解析器."""
    suffix = Path(file_path).suffix.lower()
    if suffix == ".txt":
        return _parse_txt(file_path)
    elif suffix == ".docx":
        return _parse_docx(file_path)
    elif suffix == ".epub":
        return _parse_epub(file_path)
    else:
        raise ValidationError(
            error_code=ErrorCode.VALIDATION_ERROR,
            detail=f"不支持的文件格式：{suffix}，支持 txt / docx / epub",
        )


def _extract_metadata_from_filename(file_path: str) -> dict[str, str]:
    """从文件名尝试提取标题和作者.

    常见命名: 《书名》-作者.txt / 书名_作者.txt
    """
    stem = Path(file_path).stem
    title = ""
    author = ""

    # 《书名》-作者
    m = re.match(r"[《](.+)[》][\s_-]*[—\-]?[\s_-]*(.+)", stem)
    if m:
        title = m.group(1).strip()
        author = m.group(2).strip()
        return {"title": title, "author": author}

    # 书名_作者
    m = re.match(r"(.+)[_—\-](.+)", stem)
    if m:
        title = m.group(1).strip()
        author = m.group(2).strip()
        return {"title": title, "author": author}

    # 默认用文件名作标题
    title = stem.strip()
    return {"title": title, "author": author}


def _count_chinese_chars(text: str) -> int:
    """统计中文字符数."""
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def _count_words(text: str) -> int:
    """统计总字数（中文 + 英文单词）."""
    chinese = _count_chinese_chars(text)
    english = len(re.findall(r"[a-zA-Z]+", text))
    return chinese + english


# ---------------------------------------------------------------------------
# ImportService
# ---------------------------------------------------------------------------


class ImportService:
    """文件导入服务：解析上传文件、拆章、写入数据库并分析."""

    async def import_book(
        self,
        project_id: int,
        file_path: str,
        import_mode: str = "replace",
    ) -> dict:
        """导入书籍文件，创建项目章节结构。

        Args:
            project_id: 项目 ID
            file_path: 上传文件的绝对路径
            import_mode: 导入模式 "replace"（替换全部）/ "append"（追加）

        Returns:
            {"status": "success", "project_id": ..., "chapters_count": ..., "total_words": ...}
        """
        logger.info("开始导入书籍 project=%s path=%s mode=%s", project_id, file_path, import_mode)

        if not os.path.exists(file_path):
            raise ValidationError(
                error_code=ErrorCode.VALIDATION_ERROR,
                detail=f"文件不存在：{file_path}",
            )

        # 1. 解析文件
        raw_text = _parse_file(file_path)
        if not raw_text or not raw_text.strip():
            raise ValidationError(
                error_code=ErrorCode.VALIDATION_ERROR,
                detail="文件内容为空，无法导入",
            )

        # 2. 拆分章节
        raw_chapters = _split_chapters(raw_text)
        if not raw_chapters:
            raise ValidationError(
                error_code=ErrorCode.VALIDATION_ERROR,
                detail="未检测到章节结构，请确认文件内容格式",
            )

        logger.info("检测到 %d 个章节", len(raw_chapters))

        # 3. 提取元数据
        meta = _extract_metadata_from_filename(file_path)

        # 4. 写入数据库
        session_factory = _get_session_factory()
        async with session_factory() as db:
            # 获取项目
            project = await project_dao.get(db, project_id)
            if project is None:
                raise NotFoundError(
                    error_code=ErrorCode.PROJECT_NOT_FOUND,
                    detail="项目不存在",
                )

            # 替换模式：先清空已有章节
            if import_mode == "replace":
                existing = await chapter_dao.get_by_project(db, project_id, limit=10000)
                for ch in existing:
                    await db.delete(ch)
                await db.flush()

            # 获取当前最大章节号
            max_num = await chapter_dao.get_max_chapter_number(db, project_id)

            total_words = 0
            for idx, ch in enumerate(raw_chapters, start=1):
                word_count = _count_words(ch["content"])

                chapter = Chapter(
                    project_id=project_id,
                    title=ch["title"],
                    content=ch["content"],
                    chapter_number=max_num + idx,
                    word_count=word_count,
                    status="completed",
                )
                db.add(chapter)
                total_words += word_count

            # 更新项目元数据
            if import_mode == "replace":
                # 仅当元数据为空时用文件名覆盖
                if not project.author or project.author.strip() == "":
                    if meta.get("author"):
                        project.author = meta["author"]
                if not project.title or project.title.strip() == "":
                    if meta.get("title"):
                        project.title = meta["title"]

            # 更新项目字数
            if import_mode == "replace":
                project.word_count = total_words
            else:
                project.word_count = (project.word_count or 0) + total_words

            await db.commit()

        logger.info("导入完成：project=%s 章节=%d 总字数=%d", project_id, len(raw_chapters), total_words)

        return {
            "status": "success",
            "project_id": project_id,
            "chapters_count": len(raw_chapters),
            "total_words": total_words,
        }

    async def analyze_content(self, project_id: int) -> dict:
        """分析项目内容，生成章节结构和文风指标。

        Args:
            project_id: 项目 ID

        Returns:
            {
                "project_id": ...,
                "structure": {...},
                "style": {...},
                "suggestions": [...],
            }
        """
        logger.info("开始分析项目内容 project=%s", project_id)

        session_factory = _get_session_factory()
        async with session_factory() as db:
            # 获取项目
            project = await project_dao.get(db, project_id)
            if project is None:
                raise NotFoundError(
                    error_code=ErrorCode.PROJECT_NOT_FOUND,
                    detail="项目不存在",
                )

            # 获取所有章节
            chapters = await chapter_dao.get_by_project(db, project_id, limit=10000)

            if not chapters:
                return {
                    "project_id": project_id,
                    "structure": {},
                    "style": {},
                    "suggestions": [],
                }

            # ---- 章节结构分析 ----
            word_counts = [ch.word_count for ch in chapters]
            total_words = sum(word_counts)
            chapter_count = len(chapters)
            avg_words = total_words / chapter_count if chapter_count else 0
            word_count_std = 0.0
            if len(word_counts) > 1:
                mean = total_words / len(word_counts)
                word_count_std = (
                    sum((w - mean) ** 2 for w in word_counts) / len(word_counts)
                ) ** 0.5

            # 字数分布
            word_distribution = {
                "min": min(word_counts) if word_counts else 0,
                "max": max(word_counts) if word_counts else 0,
                "avg": round(avg_words, 1),
                "std": round(word_count_std, 1),
            }

            # 章节完成率
            completed = sum(1 for ch in chapters if ch.status == "completed")
            completion_rate = completed / chapter_count if chapter_count else 0

            structure = {
                "total_chapters": chapter_count,
                "total_words": total_words,
                "avg_words_per_chapter": round(avg_words, 1),
                "word_count_distribution": word_distribution,
                "chapter_completion_rate": round(completion_rate * 100, 1),
            }

            # ---- 文风分析 ----
            style = self._analyze_style(chapters)

            # ---- 生成建议 ----
            suggestions = self._generate_suggestions(
                chapter_count=chapter_count,
                total_words=total_words,
                avg_words=avg_words,
                word_count_std=word_count_std,
                completion_rate=completion_rate,
                project_status=project.status,
            )

            return {
                "project_id": project_id,
                "structure": structure,
                "style": style,
                "suggestions": suggestions,
            }

    # ------------------------------------------------------------------
    # 文风分析私有方法
    # ------------------------------------------------------------------

    @staticmethod
    def _analyze_style(chapters: list) -> dict:
        """分析章节文本的写作风格指标."""
        if not chapters:
            return {}

        all_text = ""
        for ch in chapters:
            if ch.content:
                all_text += ch.content + "\n"

        if not all_text.strip():
            return {}

        # 总字符数
        total_chars = len(all_text)

        # 句子分析
        sentences = re.split(r"[。！？\.!?\n]", all_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if sentences:
            avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)
        else:
            avg_sentence_length = 0

        # 对话比例（引号包围的文本占比）
        dialogue_matches = re.findall(
            r'[\u201c\u201d\u300c\u300e]([^\u201d\u201c\u300d\u300f]*)[\u201d\u201c\u300d\u300f]',
            all_text,
        )
        dialogue_chars = sum(len(m) for m in dialogue_matches)
        dialogue_ratio = dialogue_chars / total_chars if total_chars else 0

        # 段落统计
        paragraphs = [p.strip() for p in all_text.split("\n") if p.strip()]
        avg_paragraph_length = (
            sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0
        )

        # 标点使用频率
        punctuation_marks = {
            "逗号": all_text.count("，"),
            "句号": all_text.count("。"),
            "感叹号": all_text.count("！"),
            "问号": all_text.count("？"),
            "省略号": all_text.count("……") + all_text.count("..."),
        }

        return {
            "total_chars": total_chars,
            "avg_sentence_length": round(avg_sentence_length, 1),
            "dialogue_ratio": round(dialogue_ratio * 100, 1),
            "paragraph_count": len(paragraphs),
            "avg_paragraph_length": round(avg_paragraph_length, 1),
            "punctuation_usage": punctuation_marks,
        }

    @staticmethod
    def _generate_suggestions(
        chapter_count: int,
        total_words: int,
        avg_words: float,
        word_count_std: float,
        completion_rate: float,
        project_status: str,
    ) -> list[dict[str, str]]:
        """基于分析结果生成写作建议."""
        suggestions: list[dict[str, str]] = []

        # 章节数量
        if chapter_count == 0:
            suggestions.append({
                "type": "structure",
                "title": "尚无章节",
                "content": "项目目前没有章节内容，建议先导入文稿或手动创建章节。",
                "priority": "high",
            })
            return suggestions

        if chapter_count < 3:
            suggestions.append({
                "type": "structure",
                "title": "章节数量较少",
                "content": f"当前只有 {chapter_count} 个章节，建议完成更多章节以更好地分析整体结构和节奏。",
                "priority": "medium",
            })

        # 章节平均字数
        if 0 < avg_words < 500:
            suggestions.append({
                "type": "word_count",
                "title": "章节字数偏少",
                "content": f"平均每章仅 {avg_words:.0f} 字，网文通常每章 2000–5000 字，建议扩充内容。",
                "priority": "medium",
            })
        elif avg_words > 10000:
            suggestions.append({
                "type": "word_count",
                "title": "章节字数偏多",
                "content": f"平均每章 {avg_words:.0f} 字，可能造成阅读负担，建议拆分为更短的章节。",
                "priority": "low",
            })

        # 字数分布不均
        if word_count_std > 3000:
            suggestions.append({
                "type": "structure",
                "title": "章节长度波动较大",
                "content": "章节字数差异显著（标准差大），建议保持每章长度相对均匀，以提升阅读体验。",
                "priority": "medium",
            })

        # 完成率
        if completion_rate < 0.5 and chapter_count > 0:
            suggestions.append({
                "type": "completion",
                "title": "章节完成率较低",
                "content": f"当前完成率为 {completion_rate * 100:.1f}%，建议优先完成草稿章节后再进行精修。",
                "priority": "high",
            })

        # 总字数
        if 0 < total_words < 10000:
            suggestions.append({
                "type": "scale",
                "title": "作品篇幅偏短",
                "content": f"当前总计 {total_words} 字，建议继续扩充内容以构建完整的故事。",
                "priority": "medium",
            })

        # 项目状态
        if project_status == "draft" and total_words > 50000:
            suggestions.append({
                "type": "progress",
                "title": "已具备规模，可以开始精修",
                "content": f"当前已有 {total_words} 字草稿，建议将状态切换为 active 并开始精修。",
                "priority": "medium",
            })

        return suggestions


# ---------------------------------------------------------------------------
# 模块级单例
# ---------------------------------------------------------------------------

import_service = ImportService()
