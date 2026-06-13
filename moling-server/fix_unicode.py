"""修复性能测试脚本的Unicode编码问题."""

import sys
import os

def fix_unicode_issues():
    """修复Unicode编码问题."""
    print("修复性能测试脚本的Unicode编码问题...")
    
    # 设置环境变量
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONLEGACYWINDOWSSTDIO"] = "utf-8"
    
    # 需要修复的文件
    files_to_fix = [
        "tests/performance/simple_perf_test.py",
        "tests/performance/rate_limited_test.py"
    ]
    
    for file_path in files_to_fix:
        print(f"\n检查文件: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"  ⚠️  文件不存在，跳过")
            continue
        
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有Unicode字符
        if '\u2705' in content or '\u274c' in content or '\u26a0\ufe0f' in content:
            print(f"  发现Unicode字符，正在修复...")
            
            # 替换Unicode字符为ASCII字符
            content = content.replace('\u2705', '[PASS]')  # ✅
            content = content.replace('\u274c', '[FAIL]')  # ❌
            content = content.replace('\u26a0\ufe0f', '[WARN]')  # ⚠️
            
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"  ✅ 已修复")
        else:
            print(f"  ✅ 没有Unicode问题")
    
    print("\n修复完成！")

if __name__ == "__main__":
    fix_unicode_issues()
