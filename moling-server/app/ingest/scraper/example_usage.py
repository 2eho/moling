"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
example_usage.py
app.ingest.scraper 使用示例
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

运行:
    pip install requests beautifulsoup4 trafilatura
    python example_usage.py
"""

import json
import sys
import os

# 确保能导入本模块
sys.path.insert(0, os.path.dirname(__file__))

import app.ingest.scraper as nd
from app.ingest.scraper.export import to_summary_json, to_plain_text, to_markdown, to_chunks
from app.ingest.scraper.splitter.strategies import list_strategies


def main():
    # ────────────────────────────────────────────────────
    # 示例 1: 从纯文本拆解（最常见场景）
    # ────────────────────────────────────────────────────
    print("=" * 60)
    print("示例 1: 从纯文本拆解")
    print("=" * 60)

    sample_text = """
第一章 穿越异界

张明睁开眼睛，发现自己躺在一片荒草地上。
天空是紫色的，远处有三轮月亮悬挂在天际。
"这是什么地方？"他喃喃自语。

"你终于醒了。"一个清脆的声音响起。
张明转过头，看见一个穿着白色长裙的女孩正看着他。
"你是谁？这里是哪里？"
女孩微微一笑："这里是玄天大陆，我是你的引导者，你可以叫我小月。"

第二章 初遇危机

第二天一早，张明被一阵喧闹声吵醒。
他走出帐篷，看到村口聚集了一群人。
"妖兽来袭！"有人高声喊道。
张明心中一惊，握紧了腰间的长剑。

第三章 觉醒之力

就在妖兽即将扑到面前的瞬间，
张明忽然感到体内涌出一股热流。
他的手掌亮起了金色的光芒。
"这是……我的力量？"

第四章 新的征程

战斗结束后，张明决定离开村子去冒险。
小月递给他一张地图："这是整个玄天大陆的地图。"
张明接过地图，目光坚定地看着远方。
"好，那就开始我的冒险吧！"
""".strip()

    result = nd.dissect_text(
        text=sample_text,
        title="异界冒险录",
        split_strategies=["chapter_regex", "paragraph"],
    )

    print(f"书名: {result.title}")
    print(f"章节数: {result.chapter_count}")
    print(f"总字数: {result.total_word_count}")
    print()

    for ch in result.chapters:
        print(f"  第{ch.index}章: {ch.title} ({ch.word_count}字)")
        if ch.paragraphs:
            for p in ch.paragraphs[:2]:  # 只打印前 2 段
                print(f"    段{p.index}: {p.text[:40]}...")
        print()

    # ────────────────────────────────────────────────────
    # 示例 2: 输出 JSON
    # ────────────────────────────────────────────────────
    print("=" * 60)
    print("示例 2: JSON 输出（供后端消费）")
    print("=" * 60)
    print(result.json(indent=2)[:500])
    print("...")

    # ────────────────────────────────────────────────────
    # 示例 3: 摘要 JSON（不含正文）
    # ────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("示例 3: 摘要 JSON（仅元数据）")
    print("=" * 60)
    summary = to_summary_json(result)
    print(summary[:400])
    print("...")

    # ────────────────────────────────────────────────────
    # 示例 4: 输出为纯文本 / Markdown
    # ────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("示例 4: Markdown 输出")
    print("=" * 60)
    md = to_markdown(result)
    print(md[:400])
    print("...")

    # ────────────────────────────────────────────────────
    # 示例 5: 分片输出（适合 API 流式）
    # ────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("示例 5: 分片输出（每片 2 章）")
    print("=" * 60)
    chunks = to_chunks(result, max_chunk_chapters=2)
    for chunk in chunks:
        print(f"  片{chunk['chunk_index']}: 章{chunk['chapter_start']}-章{chunk['chapter_end']} ({chunk['chapter_count']}章)")

    # ────────────────────────────────────────────────────
    # 示例 6: 已注册的策略
    # ────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("示例 6: 可用拆分策略")
    print("=" * 60)
    for s in list_strategies():
        print(f"  - {s}")

    # ────────────────────────────────────────────────────
    # 示例 7: 从 HTML 拆解（需网络）
    # ────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("示例 7: 从 HTML 字符串拆解")
    print("=" * 60)

    sample_html = """
<html><head><title>异界冒险录 - 免费在线阅读</title></head>
<body>
<div id="content">
第一章 穿越
<p>张明睁开眼睛，发现自己躺在一片荒草地上。</p>
<p>天空是紫色的，远处有三轮月亮。</p>
第二章 初遇危机
<p>第二天一早，张明被一阵喧闹声吵醒。</p>
第三章 觉醒
<p>张明体内涌出一股热流，手掌亮起了金光。</p>
</div>
</body></html>
"""

    html_result = nd.dissect_html(
        raw_html=sample_html,
        source_url="https://example.com/novel/1",
    )
    print(f"章节数: {html_result.chapter_count}")
    for ch in html_result.chapters:
        print(f"  {ch.title} ({ch.word_count}字)")


if __name__ == "__main__":
    main()
