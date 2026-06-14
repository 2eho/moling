"""
墨灵 (Moling) - 全功能自动化测试套件
测试范围：认证、项目、章节、卡牌、世界观库、生成管线
"""
import requests
import json
import time
import sys
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = f"test_{int(time.time())}@moling.com"
TEST_PASSWORD = "Test123456"
TEST_NICKNAME = "测试用户"

# 全局变量
access_token = None
user_id = None
project_id = None
chapter_id = None
test_results = []
failed_tests = []

def log(test_name, success, message="", response=None):
    """记录测试结果"""
    status = "✅ PASS" if success else "❌ FAIL"
    result = {
        "test": test_name,
        "status": status,
        "message": message,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    
    if response:
        result["status_code"] = response.status_code
        if not success:
            result["response"] = response.text[:200]
    
    test_results.append(result)
    
    if not success:
        failed_tests.append(result)
    
    print(f"  {status} {test_name}")
    if message:
        print(f"         └─ {message}")
    if not success and response:
        print(f"         └─ Status: {response.status_code}, Response: {response.text[:150]}")


def test_01_health_check():
    """测试1: 健康检查"""
    print("\n[1/20] 健康检查")
    try:
        resp = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health", timeout=5)
        log("健康检查", resp.status_code == 200, f"Status: {resp.status_code}")
        return resp.status_code == 200
    except Exception as e:
        log("健康检查", False, str(e))
        return False


def test_02_register():
    """测试2: 用户注册"""
    print("\n[2/20] 用户注册")
    global access_token, user_id
    
    try:
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "email": TEST_EMAIL,
            "nickname": TEST_NICKNAME,
            "password": TEST_PASSWORD
        }, timeout=10)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            access_token = data["access_token"]
            user_id = data["user"]["id"]
            log("用户注册", True, f"User ID: {user_id}, Email: {TEST_EMAIL}")
            return True
        else:
            log("用户注册", False, response=resp)
            return False
    except Exception as e:
        log("用户注册", False, str(e))
        return False


def test_03_login():
    """测试3: 用户登录"""
    print("\n[3/20] 用户登录")
    global access_token, user_id
    
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            access_token = data["access_token"]
            user_id = data["user"]["id"]
            log("用户登录", True, f"Token acquired")
            return True
        else:
            log("用户登录", False, response=resp)
            return False
    except Exception as e:
        log("用户登录", False, str(e))
        return False


def test_04_get_profile():
    """测试4: 获取用户资料"""
    print("\n[4/20] 获取用户资料")
    
    try:
        resp = requests.get(f"{BASE_URL}/auth/me", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            log("获取用户资料", True, f"Email: {data.get('email')}")
            return True
        else:
            log("获取用户资料", False, response=resp)
            return False
    except Exception as e:
        log("获取用户资料", False, str(e))
        return False


def test_05_create_project():
    """测试5: 创建项目"""
    print("\n[5/20] 创建项目")
    global project_id
    
    try:
        resp = requests.post(f"{BASE_URL}/projects", json={
            "name": "测试小说项目",
            "description": "这是一个自动化测试创建的项目",
            "genre": "奇幻",
            "target_words": 100000
        }, headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            project_id = data["id"]
            log("创建项目", True, f"Project ID: {project_id}")
            return True
        else:
            log("创建项目", False, response=resp)
            return False
    except Exception as e:
        log("创建项目", False, str(e))
        return False


def test_06_get_projects():
    """测试6: 获取项目列表"""
    print("\n[6/20] 获取项目列表")
    
    try:
        resp = requests.get(f"{BASE_URL}/projects", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            log("获取项目列表", True, f"Count: {len(data) if isinstance(data, list) else 'N/A'}")
            return True
        else:
            log("获取项目列表", False, response=resp)
            return False
    except Exception as e:
        log("获取项目列表", False, str(e))
        return False


def test_07_get_project_detail():
    """测试7: 获取项目详情"""
    print("\n[7/20] 获取项目详情")
    
    if not project_id:
        log("获取项目详情", False, "No project_id")
        return False
    
    try:
        resp = requests.get(f"{BASE_URL}/projects/{project_id}", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            log("获取项目详情", True, f"Name: {data.get('name')}")
            return True
        else:
            log("获取项目详情", False, response=resp)
            return False
    except Exception as e:
        log("获取项目详情", False, str(e))
        return False


def test_08_update_project():
    """测试8: 更新项目"""
    print("\n[8/20] 更新项目")
    
    if not project_id:
        log("更新项目", False, "No project_id")
        return False
    
    try:
        resp = requests.put(f"{BASE_URL}/projects/{project_id}", json={
            "name": "测试小说项目（已更新）",
            "description": "更新后的项目描述"
        }, headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            log("更新项目", True)
            return True
        else:
            log("更新项目", False, response=resp)
            return False
    except Exception as e:
        log("更新项目", False, str(e))
        return False


def test_09_create_chapter():
    """测试9: 创建章节"""
    print("\n[9/20] 创建章节")
    global chapter_id
    
    if not project_id:
        log("创建章节", False, "No project_id")
        return False
    
    try:
        resp = requests.post(f"{BASE_URL}/projects/{project_id}/chapters", json={
            "title": "第一章：开始的旅程",
            "order": 1
        }, headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            chapter_id = data["id"]
            log("创建章节", True, f"Chapter ID: {chapter_id}")
            return True
        else:
            log("创建章节", False, response=resp)
            return False
    except Exception as e:
        log("创建章节", False, str(e))
        return False


def test_10_get_chapters():
    """测试10: 获取章节列表"""
    print("\n[10/20] 获取章节列表")
    
    if not project_id:
        log("获取章节列表", False, "No project_id")
        return False
    
    try:
        resp = requests.get(f"{BASE_URL}/projects/{project_id}/chapters", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            log("获取章节列表", True, f"Count: {len(data) if isinstance(data, list) else 'N/A'}")
            return True
        else:
            log("获取章节列表", False, response=resp)
            return False
    except Exception as e:
        log("获取章节列表", False, str(e))
        return False


def test_11_get_chapter_detail():
    """测试11: 获取章节详情"""
    print("\n[11/20] 获取章节详情")
    
    if not chapter_id:
        log("获取章节详情", False, "No chapter_id")
        return False
    
    try:
        resp = requests.get(f"{BASE_URL}/chapters/{chapter_id}", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            log("获取章节详情", True, f"Title: {data.get('title')}")
            return True
        else:
            log("获取章节详情", False, response=resp)
            return False
    except Exception as e:
        log("获取章节详情", False, str(e))
        return False


def test_12_update_chapter():
    """测试12: 更新章节"""
    print("\n[12/20] 更新章节")
    
    if not chapter_id:
        log("更新章节", False, "No chapter_id")
        return False
    
    try:
        resp = requests.put(f"{BASE_URL}/chapters/{chapter_id}", json={
            "title": "第一章：旅程的开始（已更新）",
            "content": "这是章节内容..."
        }, headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            log("更新章节", True)
            return True
        else:
            log("更新章节", False, response=resp)
            return False
    except Exception as e:
        log("更新章节", False, str(e))
        return False


def test_13_draw_cards():
    """测试13: 抽卡"""
    print("\n[13/20] 抽卡")
    
    if not project_id:
        log("抽卡", False, "No project_id")
        return False
    
    try:
        resp = requests.post(f"{BASE_URL}/projects/{project_id}/draw", json={
            "card_ids": [],
            "weights": [],
            "mode": "balanced"
        }, headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code in [200, 201]:
            log("抽卡", True)
            return True
        else:
            # 可能端点不存在或参数不正确，记录但不失败
            log("抽卡", False, f"Endpoint may not be fully implemented: {resp.status_code}")
            return False
    except Exception as e:
        log("抽卡", False, str(e))
        return False


def test_14_get_vault_characters():
    """测试14: 获取世界观角色列表"""
    print("\n[14/20] 获取世界观角色列表")
    
    if not project_id:
        log("获取世界观角色列表", False, "No project_id")
        return False
    
    try:
        resp = requests.get(f"{BASE_URL}/projects/{project_id}/vault/characters", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            log("获取世界观角色列表", True, f"Count: {len(data) if isinstance(data, list) else 'N/A'}")
            return True
        else:
            log("获取世界观角色列表", False, response=resp)
            return False
    except Exception as e:
        log("获取世界观角色列表", False, str(e))
        return False


def test_15_create_vault_character():
    """测试15: 创建世界观角色"""
    print("\n[15/20] 创建世界观角色")
    
    if not project_id:
        log("创建世界观角色", False, "No project_id")
        return False
    
    try:
        resp = requests.post(f"{BASE_URL}/projects/{project_id}/vault/characters", json={
            "name": "测试角色",
            "description": "这是一个测试角色",
            "traits": ["勇敢", "聪明"]
        }, headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code in [200, 201]:
            log("创建世界观角色", True)
            return True
        else:
            log("创建世界观角色", False, response=resp)
            return False
    except Exception as e:
        log("创建世界观角色", False, str(e))
        return False


def test_16_get_health_alerts():
    """测试16: 获取健康告警"""
    print("\n[16/20] 获取健康告警")
    
    if not project_id:
        log("获取健康告警", False, "No project_id")
        return False
    
    try:
        resp = requests.get(f"{BASE_URL}/projects/{project_id}/health", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            log("获取健康告警", True)
            return True
        else:
            log("获取健康告警", False, response=resp)
            return False
    except Exception as e:
        log("获取健康告警", False, str(e))
        return False


def test_17_refresh_token():
    """测试17: 刷新Token"""
    print("\n[17/20] 刷新Token")
    
    # 先登录获取refresh_token
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            refresh_token = data.get("refresh_token")
            
            if refresh_token:
                resp2 = requests.post(f"{BASE_URL}/auth/refresh", json={
                    "refresh_token": refresh_token
                }, timeout=10)
                
                if resp2.status_code == 200:
                    log("刷新Token", True)
                    return True
                else:
                    log("刷新Token", False, response=resp2)
                    return False
            else:
                log("刷新Token", False, "No refresh_token in login response")
                return False
        else:
            log("刷新Token", False, "Login failed, cannot get refresh_token")
            return False
    except Exception as e:
        log("刷新Token", False, str(e))
        return False


def test_18_unauthorized_access():
    """测试18: 未授权访问测试"""
    print("\n[18/20] 未授权访问测试")
    
    try:
        resp = requests.get(f"{BASE_URL}/projects", timeout=10)
        
        # 应该返回401或403
        if resp.status_code in [401, 403]:
            log("未授权访问测试", True, "Correctly rejected")
            return True
        else:
            log("未授权访问测试", False, f"Expected 401/403, got {resp.status_code}")
            return False
    except Exception as e:
        log("未授权访问测试", False, str(e))
        return False


def test_19_invalid_token():
    """测试19: 无效Token测试"""
    print("\n[19/20] 无效Token测试")
    
    try:
        resp = requests.get(f"{BASE_URL}/projects", headers={
            "Authorization": "Bearer invalid_token_here"
        }, timeout=10)
        
        # 应该返回401
        if resp.status_code == 401:
            log("无效Token测试", True, "Correctly rejected")
            return True
        else:
            log("无效Token测试", False, f"Expected 401, got {resp.status_code}")
            return False
    except Exception as e:
        log("无效Token测试", False, str(e))
        return False


def test_20_delete_chapter():
    """测试20: 删除章节"""
    print("\n[20/20] 删除章节")
    
    if not chapter_id:
        log("删除章节", False, "No chapter_id")
        return False
    
    try:
        resp = requests.delete(f"{BASE_URL}/chapters/{chapter_id}", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code in [200, 204]:
            log("删除章节", True)
            return True
        else:
            log("删除章节", False, response=resp)
            return False
    except Exception as e:
        log("删除章节", False, str(e))
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🚀 墨灵项目 - 全功能自动化测试")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试用户: {TEST_EMAIL}")
    print(f"后端地址: {BASE_URL}")
    print("=" * 60)
    
    # 执行测试
    tests = [
        test_01_health_check,
        test_02_register,
        test_03_login,
        test_04_get_profile,
        test_05_create_project,
        test_06_get_projects,
        test_07_get_project_detail,
        test_08_update_project,
        test_09_create_chapter,
        test_10_get_chapters,
        test_11_get_chapter_detail,
        test_12_update_chapter,
        test_13_draw_cards,
        test_14_get_vault_characters,
        test_15_create_vault_character,
        test_16_get_health_alerts,
        test_17_refresh_token,
        test_18_unauthorized_access,
        test_19_invalid_token,
        test_20_delete_chapter,
    ]
    
    for test in tests:
        try:
            test()
            time.sleep(0.5)  # 避免请求过快
        except Exception as e:
            log(test.__name__, False, f"Test execution error: {str(e)}")
    
    # 生成报告
    print("\n" + "=" * 60)
    print("📊 测试报告")
    print("=" * 60)
    
    total = len(test_results)
    passed = len([r for r in test_results if "PASS" in r["status"]])
    failed = len(failed_tests)
    
    print(f"\n总测试数: {total}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"通过率: {passed/total*100:.1f}%")
    
    if failed_tests:
        print("\n❌ 失败的测试:")
        for t in failed_tests:
            print(f"  - {t['test']}: {t.get('message', 'Unknown error')}")
    
    print("\n" + "=" * 60)
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 保存报告
    report = {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed/total*100:.1f}%"
        },
        "details": test_results
    }
    
    with open("C:/Users/Admin/Desktop/新建文件夹 (2)/test_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("\n📝 详细报告已保存到: test_report.json")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
