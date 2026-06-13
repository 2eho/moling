"""测试完全同步数据库模式."""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_register_sync():
    """测试注册功能 - 使用同步方式."""
    print("测试: 尝试访问注册端点 (GET)")
    print("="*60)
    
    # 先检查注册端点是否存在
    try:
        response = requests.get(f"{BASE_URL}/api/v1/auth/register", timeout=5)
        print(f"GET /api/v1/auth/register 状态码: {response.status_code}")
        print(f"响应: {response.text[:200]}")
    except Exception as e:
        print(f"错误: {e}")
    
    print("\n" + "="*60)
    print("分析:")
    print("="*60)
    print("如果GET请求也失败，说明后端应用有问题，而不仅仅是数据库操作。")
    print("如果GET请求成功（返回405 Method Not Allowed），说明端点存在，但POST请求有问题。")

if __name__ == "__main__":
    test_register_sync()
