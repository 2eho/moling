#!/usr/bin/env python3
"""Windows 兼容的集成测试脚本 — 跳过数据库测试。"""

import platform
import sys

if platform.system() == "Windows":
    print("=" * 60)
    print("墨灵 (Moling) 集成测试 — Windows 模式")
    print("=" * 60)
    print("\n⚠️  Windows 环境检测到数据库兼容性问题。")
    print("   跳过需要数据库的测试（认证、项目、章节、四库）。")
    print("\n✅ 将运行以下测试：")
    print("   - 健康检查")
    print("   - 前端-后端联调")
    print("   - 错误处理")
    print("\n")
    
    # 直接调用原测试脚本（它会处理跳过逻辑）
    from tests.integration.run_integration_tests import main
    main()
else:
    # 非 Windows 环境，运行完整测试
    from tests.integration.run_integration_tests import main
    main()
