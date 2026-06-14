# -*- coding: utf-8 -*-
"""\u9a8c\u8bc1\u6d4b\u8bd5"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from novel_dissector.core.cleaner import clean_html, is_chapter_heading
from novel_dissector.splitter.chapter import ChapterRegexSplitter
from novel_dissector.splitter.strategies import list_strategies
from novel_dissector.pipeline import dissect_text
from novel_dissector.config import default_config

errors = []

def test(name, ok, msg=""):
    if ok:
        print(f"  PASS: {name}")
    else:
        print(f"  FAIL: {name} - {msg}")
        errors.append(name)

# 1. Cleaner
print("=== 1. Cleaner ===")
html = '<html><body><script>alert(1)</script><div id="content"><p>\u7b2c\u4e00\u7ae0 \u7a7f\u8d8a</p><p>\u6b63\u6587\u5185\u5bb9\u3002</p></div></body></html>'
cleaned = clean_html(html)
test("cleaner produces text", bool(cleaned))
test("cleaner contains title", "\u7b2c\u4e00\u7ae0 \u7a7f\u8d8a" in cleaned)
test("cleaner contains content", "\u6b63\u6587\u5185\u5bb9" in cleaned)

# 2. Chapter heading detection
print("=== 2. Chapter heading ===")
tests_data = [
    ("\u7b2c\u4e00\u7ae0 \u7a7f\u8d8a", True),
    ("\u7b2c100\u7ae0 \u5b8c\u7ed3", True),
    ("\u5e8f\u7ae0", True),
    ("\u6954\u5b50", True),
    ("\u4e0d\u662f\u6807\u9898", False),
]
for text, expected in tests_data:
    test(f"heading: {text}", is_chapter_heading(text) == expected)

# 3. Chapter splitter
print("=== 3. Chapter splitter ===")
text = (
    "\u7b2c\u4e00\u7ae0 \u7a7f\u8d8a\u5f02\u754c\n\n"
    "\u5f20\u660e\u7761\u5f00\u773c\u775b\uff0c\u53d1\u73b0\u81ea\u5df1\u8eba\u5728\u4e00\u7247\u8352\u8349\u5730\u4e0a\u3002\n\n"
    "\u7b2c\u4e8c\u7ae0 \u521d\u9047\u5371\u673a\n\n"
    "\u7b2c\u4e8c\u5929\u4e00\u65e9\uff0c\u5f20\u660e\u88ab\u4e00\u9635\u5d29\u95f9\u58f0\u5435\u9192\u3002\n\n"
    "\u7b2c\u4e09\u7ae0 \u89c9\u9192\u4e4b\u529b\n\n"
    "\u5f20\u660e\u4f53\u5185\u6d8c\u51fa\u4e00\u80a1\u70ed\u6d41\u3002"
)
splitter = ChapterRegexSplitter(min_chapter_chars=1)
chapters = splitter.split(text)
test(f"chapter count == 3", len(chapters) == 3, f"got {len(chapters)}")
for ch in chapters:
    print(f"  ch{ch.index}: [{ch.title}] ({ch.word_count} chars)")
# Verify titles
titles = [ch.title for ch in chapters]
test("chapter 1 title correct", "\u7b2c\u4e00\u7ae0 \u7a7f\u8d8a\u5f02\u754c" in titles)
test("chapter 2 title correct", "\u7b2c\u4e8c\u7ae0 \u521d\u9047\u5371\u673a" in titles)
test("chapter 3 title correct", "\u7b2c\u4e09\u7ae0 \u89c9\u9192\u4e4b\u529b" in titles)

# 4. Pipeline
print("=== 4. Pipeline ===")
cfg = default_config()
cfg.min_chapter_chars = 1
cfg.min_para_chars = 1
cfg.merge_short_lines = False
result = dissect_text(text, title="\u6d4b\u8bd5\u5c0f\u8bf4", config=cfg)
test("pipeline chapter count", result.chapter_count == 3, f"got {result.chapter_count}")
test("pipeline no errors", len(result.errors) == 0, str(result.errors))

# 5. JSON output
print("=== 5. JSON ===")
j = result.json(indent=2)
parsed = json.loads(j)
test("JSON chapter count", parsed["chapter_count"] == 3)
# Check chapter-level structure
test("JSON has chapters array", len(parsed.get("chapters", [])) == 3)

# 6. Paragraph splitting
print("=== 6. Paragraph ===")
test("paragraphs exist in chapters", all(len(ch.paragraphs) > 0 for ch in result.chapters))

# 7. Strategies
print("=== 7. Strategies ===")
strategies = list_strategies()
test("chapter_regex registered", "chapter_regex" in strategies)
test("paragraph registered", "paragraph" in strategies)
test("3 strategies registered", len(strategies) == 3)

print()
if errors:
    print(f"FAILED: {len(errors)} tests: {errors}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
