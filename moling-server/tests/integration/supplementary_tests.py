"""补充集成测试 - 测试健康检查和错误处理。"""
import requests
import sys

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

def test_health():
    resp = requests.get(f"{BASE_URL}{API_PREFIX}/health", timeout=5)
    return resp.status_code == 200

def test_error_handling():
    # 无 Token
    resp = requests.get(f"{BASE_URL}{API_PREFIX}/auth/me", timeout=5)
    if resp.status_code not in (401, 403):
        return False
    
    # 无效 Token
    resp = requests.get(
        f"{BASE_URL}{API_PREFIX}/auth/me",
        headers={"Authorization": "Bearer invalid"},
        timeout=5
    )
    if resp.status_code not in (401, 403):
        return False
    
    # 无效请求体
    resp = requests.post(
        f"{BASE_URL}{API_PREFIX}/auth/register",
        json={"email": "invalid", "password": "123"},
        timeout=10
    )
    if resp.status_code not in (400, 422):
        return False
    
    return True

if __name__ == "__main__":
    print("运行补充集成测试...")
    
    passed = 0
    failed = 0
    
    print("  测试健康检查...")
    if test_health():
        print("    ✅ 通过")
        passed += 1
    else:
        print("    ❌ 失败")
        failed += 1
    
    print("  测试错误处理...")
    if test_error_handling():
        print("    ✅ 通过")
        passed += 1
    else:
        print("    ❌ 失败")
        failed += 1
    
    print(f"\n总计: {passed + failed} 个测试")
    print(f"  通过: {passed}")
    print(f"  失败: {failed}")
    
    sys.exit(0 if failed == 0 else 1)
