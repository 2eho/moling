"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
app.ingest.scraper / core / cleaner.py
HTML → 纯净中文正文的清洗管线
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

移植自写作猫 Go 版 scraper.go 的 CleanHTML 完整逻辑，
适配为纯 Python 实现（标准库 + 无额外依赖）。

清洗管线（8 道工序）：
  1. 移除 script / style / noscript 标签块
  2. 块级标签转换行 + 移除剩余 HTML 标签
  3. HTML 实体解码（&nbsp; &amp; 等）
  4. Unicode 转义解码（\\uXXXX）
  5. 换行符归一化（\\r\\n → \\n）
  6. 空白合并（连续空格/制表符 → 单个空格）
  7. 广告/干扰行过滤（17+ 种已知模式）
  8. 多余空行合并

参考来源
  - 写作猫项目 scraper.go (CleanHTML, removeBlocks, decodeUnicode,
    commonAds, isNumericLine, isAdLine)
  - Novel-Split (Anning01/novel-split) chapter detection patterns
"""

from __future__ import annotations

import re


# =========================================================================
# 1. 标签块移除
# =========================================================================

def remove_blocks(text: str, tag: str) -> str:
    """
    移除指定标签块及其内容（含标签自身）。
    与 Go 版 removeBlocks 逻辑一致：从后往前删，保持索引正确。
    """
    pattern = re.compile(
        rf'<{tag}[^>]*>.*?</{tag}\s*>',
        re.IGNORECASE | re.DOTALL,
    )
    return pattern.sub('', text)


def strip_html_tags(text: str) -> str:
    """
    先转块级标签为换行，再移除剩余所有 HTML 标签。
    """
    text = re.sub(r'(?i)<br\s*/?>', '\n', text)
    text = re.sub(r'(?i)</(p|div|dd|dt|li|tr|h[1-6])\s*>', '\n', text)
    text = re.sub(r'<[^>]*>', '', text)
    return text


# =========================================================================
# 2. 解码
# =========================================================================

def decode_html_entities(text: str) -> str:
    """常见的 HTML 实体 / 数值实体 → 对应字符。"""
    replacements = [
        ("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
        ("&quot;", '"'), ("&apos;", "'"), ("&#39;", "'"), ("&#34;", '"'),
        ("&#160;", " "),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    # 通用数值实体
    text = re.sub(
        r'&#(\d+);',
        lambda m: chr(int(m.group(1))) if 32 <= int(m.group(1)) <= 0x10FFFF else m.group(0),
        text,
    )
    text = re.sub(
        r'&#x([0-9a-fA-F]+);',
        lambda m: chr(int(m.group(1), 16)) if 32 <= int(m.group(1), 16) <= 0x10FFFF else m.group(0),
        text,
    )
    return text


def decode_unicode_escapes(text: str) -> str:
    """解码 \\uXXXX 形式的 Unicode 转义序列。"""
    return re.sub(
        r'\\u([0-9a-fA-F]{4})',
        lambda m: chr(int(m.group(1), 16)),
        text,
    )


# =========================================================================
# 3. 广告/干扰检测
# =========================================================================

# 已知中文盗版站广告模式（来自 scraper.go commonAds 扩展）
KNOWN_AD_PATTERNS: list[str] = [
    "本章未完，请点击下一页继续阅读",
    "请记住本书首发域名",
    "手机用户请浏览",
    "天才一秒记住",
    "提供无弹窗阅读体验",
    "内容未完，下一页继续",
    "章节错误，点此举报",
    "一秒记住",
    "为您提供",
    "新书推荐",
    "推荐阅读",
    "bookmark",
    "本站所有小说为转载作品",
    "如果您发现本站内容",
    "如果侵犯到您的权益",
    "请发邮件",
    "版权归作者所有",
]


def is_numeric_line(line: str) -> bool:
    """纯数字/标点行（页码）。至少含一个数字且全部由数字组成。"""
    stripped = line.strip()
    if not stripped:
        return False
    digit_count = sum(1 for ch in stripped if ch.isdigit())
    return digit_count > 0 and digit_count == len(stripped)


def is_ad_line(line: str) -> bool:
    """检测是否匹配已知广告模式。"""
    lower = line.lower()
    for ad in KNOWN_AD_PATTERNS:
        if ad.lower() in lower:
            return True
    return False


def is_chapter_heading(line: str) -> bool:
    """检测是否章节标题行（用于在 CleanChapterContent 中跳过）。"""
    # 第X章 / 第X节 / 序章 / 楔子
    if re.match(r'^\s*第[零一二三四五六七八九十百千万\d]+章', line):
        return True
    if re.match(r'^\s*第\d+节\s*', line):
        return True
    if re.match(r'^\s*(序章|楔子|尾声|后记|番外|前言|引子)\s*', line):
        return True
    # 纯数字编号 + 点/顿号（如 "001." / "1、"）
    if re.match(r'^\s*\d+\s*[\.、]\s*', line):
        return True
    return False


# =========================================================================
# 4. 主清洗管线
# =========================================================================

def clean_html(raw_html: str) -> str:
    """
    完整 HTML 清洗管线（对标 Go CleanHTML）。

    步骤：
      1. 移除 script/style/noscript 块
      2. 转块级标签为换行 → 移除剩余标签
      3. HTML 实体解码（含数值实体）
      4. Unicode 转义解码
      5. 换行符归一化
      6. 合并连续空白
      7. 逐行过滤（空行 / 纯数字 / 广告 / 短行 <4 字符）
      8. 合并多余空行
    """
    text = raw_html

    # 1. 移除标签块
    text = remove_blocks(text, "script")
    text = remove_blocks(text, "style")
    text = remove_blocks(text, "noscript")

    # 2. 块级转换行 + 去标签
    text = strip_html_tags(text)

    # 3. HTML 实体解码
    text = decode_html_entities(text)

    # 4. Unicode 转义解码
    text = decode_unicode_escapes(text)

    # 5. 换行符归一化
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 6. 合并连续空白（行内空格/制表符 → 单空格）
    text = re.sub(r'[ \t]+', ' ', text)

    # 7. 逐行过滤
    lines = text.split("\n")
    cleaned: list[str] = []
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        # 跳过纯数字行（页码）
        if is_numeric_line(trimmed):
            continue
        # 跳过超短行（导航/残留）
        if len(trimmed) < 4:
            continue
        # 跳过广告行
        if is_ad_line(trimmed):
            continue
        cleaned.append(trimmed)

    # 8. 合并多余空行
    result = "\n".join(cleaned)
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result.strip()


def clean_chapter_content(raw_text: str) -> str:
    """
    去除章节标题行，仅保留正文。
    对应 Go 版 CleanChapterContent。
    """
    lines = raw_text.split("\n")
    out: list[str] = []
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        if is_chapter_heading(trimmed):
            continue
        out.append(trimmed)
    return "\n".join(out)


# =========================================================================
# 5. 工具函数
# =========================================================================

def extract_title_from_html(html_text: str) -> str:
    """从清洗后的文本中尝试提取书名 / 章节标题。"""
    # <title>...</title>
    m = re.search(r'<title[^>]*>(.*?)</title>', html_text, re.IGNORECASE | re.DOTALL)
    if m:
        return clean_html(m.group(1)).strip()
    # <meta property="og:title" content="..."/>
    m = re.search(
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
        html_text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    return ""
