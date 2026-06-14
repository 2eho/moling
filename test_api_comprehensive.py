#!/usr/bin/env python3
"""
墨灵项目 - 全面API自动化测试套件
测试范围：认证、项目、章节、卡牌、世界观、生成管线
"""

import requests
import json
import time
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000/api/v1"
TEST_USER = {
    "email": f"test_{int(time.time())}@moling.com",
    "nickname": f"testuser_{int(time.time())}",
    "password": "Test@123456"
}

# 全局变量
access_token = None
user_id = None
project_id = None
chapter_id = None
card_id = None

# 测试结果统计
test_results = []
passed = 0
failed = 0


def log(test_name, success, message=""):
    """记录测试结果"""
    global passed, failed
    status = "✅ PASS" if success else "❌ FAIL"
    result = {
        "test": test_name,
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    test_results.append(result)
    
    if success:
        passed += 1
        print(f"  {status}: {test_name}")
    else:
        failed += 1
        print(f"  {status}: {test_name}")
        if message:
            print(f"    错误: {message[:200]}")
    
    return success


def test_01_register():
    """测试1: 用户注册"""
    print("\n[1/20] 用户注册")
    global access_token, user_id
    
    try:
        resp = requests.post(f"{BASE_URL}/auth/register", json=TEST_USER, timeout=10)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            access_token = data["access_token"]
            user_id = data["user"]["id"]
            return log("用户注册", True, f"User ID: {user_id}")
        else:
            return log("用户注册", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("用户注册", False, str(e))


def test_02_login():
    """测试2: 用户登录"""
    print("\n[2/20] 用户登录")
    global access_token, user_id
    
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            access_token = data["access_token"]
            user_id = data["user"]["id"]
            return log("用户登录", True, f"Token acquired")
        else:
            return log("用户登录", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("用户登录", False, str(e))


def test_03_get_me():
    """测试3: 获取当前用户信息"""
    print("\n[3/20] 获取当前用户信息")
    
    if not access_token:
        return log("获取用户信息", False, "No access_token")
    
    try:
        resp = requests.get(f"{BASE_URL}/auth/me", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            return log("获取用户信息", True, f"Email: {data.get('email')}")
        else:
            return log("获取用户信息", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("获取用户信息", False, str(e))


def test_04_update_profile():
    """测试4: 更新用户资料"""
    print("\n[4/20] 更新用户资料")
    
    if not access_token:
        return log("更新用户资料", False, "No access_token")
    
    try:
        resp = requests.put(f"{BASE_URL}/auth/me", json={
            "username": "updated_nickname"
        }, headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            return log("更新用户资料", True)
        else:
            return log("更新用户资料", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("更新用户资料", False, str(e))


def test_05_create_project():
    """测试5: 创建项目"""
    print("\n[5/20] 创建项目")
    global project_id
    
    if not access_token:
        return log("创建项目", False, "No access_token")
    
    try:
        resp = requests.post(f"{BASE_URL}/projects", json={
            "title": "测试小说项目",
            "author": "测试作者",
            "genre": "奇幻",
            "synopsis": "这是一个自动化测试创建的项目",
            "target_words": 100000
        }, headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            project_id = data["id"]
            return log("创建项目", True, f"Project ID: {project_id}")
        else:
            return log("创建项目", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("创建项目", False, str(e))


def test_06_list_projects():
    """测试6: 获取项目列表"""
    print("\n[6/20] 获取项目列表")
    
    if not access_token:
        return log("获取项目列表", False, "No access_token")
    
    try:
        resp = requests.get(f"{BASE_URL}/projects", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            return log("获取项目列表", True, f"Count: {len(data)}")
        else:
            return log("获取项目列表", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("获取项目列表", False, str(e))


def test_07_get_project():
    """测试7: 获取项目详情"""
    print("\n[7/20] 获取项目详情")
    
    if not access_token or not project_id:
        return log("获取项目详情", False, "No access_token or project_id")
    
    try:
        resp = requests.get(f"{BASE_URL}/projects/{project_id}", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            return log("获取项目详情", True, f"Title: {data.get('title')}")
        else:
            return log("获取项目详情", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("获取项目详情", False, str(e))


def test_08_update_project():
    """测试8: 更新项目"""
    print("\n[8/20] 更新项目")
    
    if not access_token or not project_id:
        return log("更新项目", False, "No access_token or project_id")
    
    try:
        resp = requests.put(f"{BASE_URL}/projects/{project_id}", json={
            "title": "更新后的项目标题",
            "synopsis": "更新后的项目描述"
        }, headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            return log("更新项目", True)
        else:
            return log("更新项目", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("更新项目", False, str(e))


def test_09_create_chapter():
    """测试9: 创建章节"""
    print("\n[9/20] 创建章节")
    global chapter_id
    
    if not access_token or not project_id:
        return log("创建章节", False, "No access_token or project_id")
    
    try:
        resp = requests.post(f"{BASE_URL}/projects/{project_id}/chapters", json={
            "title": "第一章：开始",
            "order": 1,
            "goal_words": 2000
        }, headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            chapter_id = data["id"]
            return log("创建章节", True, f"Chapter ID: {chapter_id}")
        else:
            return log("创建章节", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("创建章节", False, str(e))


def test_10_list_chapters():
    """测试10: 获取章节列表"""
    print("\n[10/20] 获取章节列表")
    
    if not access_token or not project_id:
        return log("获取章节列表", False, "No access_token or project_id")
    
    try:
        resp = requests.get(f"{BASE_URL}/projects/{project_id}/chapters", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            return log("获取章节列表", True, f"Count: {len(data)}")
        else:
            return log("获取章节列表", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("获取章节列表", False, str(e))


def test_11_get_chapter():
    """测试11: 获取章节详情"""
    print("\n[11/20] 获取章节详情")
    
    if not access_token or not chapter_id:
        return log("获取章节详情", False, "No access_token or chapter_id")
    
    try:
        resp = requests.get(f"{BASE_URL}/chapters/{chapter_id}", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            return log("获取章节详情", True, f"Title: {data.get('title')}")
        else:
            return log("获取章节详情", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("获取章节详情", False, str(e))


def test_12_update_chapter():
    """测试12: 更新章节"""
    print("\n[12/20] 更新章节")
    
    if not access_token or not chapter_id:
        return log("更新章节", False, "No access_token or chapter_id")
    
    try:
        resp = requests.put(f"{BASE_URL}/chapters/{chapter_id}", json={
            "title": "第一章：新的开始",
            "content": "这是章节内容..."
        }, headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            return log("更新章节", True)
        else:
            return log("更新章节", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("更新章节", False, str(e))


def test_13_draw_card():
    """测试13: 抽卡"""
    print("\n[13/20] 抽卡")
    global card_id
    
    if not access_token or not project_id:
        return log("抽卡", False, "No access_token or project_id")
    
    try:
        resp = requests.post(f"{BASE_URL}/projects/{project_id}/draw", json={
            "card_type": "character"
        }, headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            card_id = data.get("id")
            return log("抽卡", True, f"Card ID: {card_id}")
        else:
            # 抽卡可能失败（如果服务未实现），记录但不中断
            return log("抽卡", False, f"Status {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        return log("抽卡", False, str(e))


def test_14_list_cards():
    """测试14: 获取卡牌列表"""
    print("\n[14/20] 获取卡牌列表")
    
    if not access_token or not project_id:
        return log("获取卡牌列表", False, "No access_token or project_id")
    
    try:
        resp = requests.get(f"{BASE_URL}/projects/{project_id}/cards", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            return log("获取卡牌列表", True, f"Count: {len(data)}")
        else:
            return log("获取卡牌列表", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("获取卡牌列表", False, str(e))


def test_15_create_vault_entry():
    """测试15: 创建世界观条目"""
    print("\n[15/20] 创建世界观条目")
    
    if not access_token or not project_id:
        return log("创建世界观条目", False, "No access_token or project_id")
    
    try:
        resp = requests.post(f"{BASE_URL}/projects/{project_id}/vault/characters", json={
            "name": "测试角色",
            "description": "这是一个测试角色",
            "traits": ["勇敢", "聪明"]
        }, headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            return log("创建世界观条目", True, f"Entry ID: {data.get('id')}")
        else:
            return log("创建世界观条目", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("创建世界观条目", False, str(e))


def test_16_get_vault():
    """测试16: 获取世界观库"""
    print("\n[16/20] 获取世界观库")
    
    if not access_token or not project_id:
        return log("获取世界观库", False, "No access_token or project_id")
    
    try:
        resp = requests.get(f"{BASE_URL}/projects/{project_id}/vault", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code == 200:
            return log("获取世界观库", True)
        else:
            return log("获取世界观库", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("获取世界观库", False, str(e))


def test_17_trigger_generation():
    """测试17: 触发生成"""
    print("\n[17/20] 触发生成")
    
    if not access_token or not project_id or not chapter_id:
        return log("触发生成", False, "No access_token, project_id or chapter_id")
    
    try:
        resp = requests.post(f"{BASE_URL}/projects/{project_id}/chapters/{chapter_id}/generate", 
            headers={
                "Authorization": f"Bearer {access_token}"
            }, timeout=10)
        
        # 生成可能是异步的，接受多个状态码
        if resp.status_code in [200, 201, 202]:
            return log("触发生成", True, f"Status: {resp.status_code}")
        else:
            return log("触发生成", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("触发生成", False, str(e))


def test_18_unauthorized_access():
    """测试18: 未授权访问测试"""
    print("\n[18/20] 未授权访问测试")
    
    try:
        resp = requests.get(f"{BASE_URL}/projects")
        
        # 应该返回401未授权
        if resp.status_code == 401:
            return log("未授权访问测试", True, "Correctly rejected")
        else:
            return log("未授权访问测试", False, f"Expected 401, got {resp.status_code}")
    except Exception as e:
        return log("未授权访问测试", False, str(e))


def test_19_invalid_token():
    """测试19: 无效Token测试"""
    print("\n[19/20] 无效Token测试")
    
    try:
        resp = requests.get(f"{BASE_URL}/projects", headers={
            "Authorization": "Bearer invalid_token_12345"
        })
        
        # 应该返回401未授权
        if resp.status_code == 401:
            return log("无效Token测试", True, "Correctly rejected")
        else:
            return log("无效Token测试", False, f"Expected 401, got {resp.status_code}")
    except Exception as e:
        return log("无效Token测试", False, str(e))


def test_20_delete_project():
    """测试20: 删除项目（清理）"""
    print("\n[20/20] 删除项目（清理测试数据）")
    
    if not access_token or not project_id:
        return log("删除项目", False, "No access_token or project_id")
    
    try:
        resp = requests.delete(f"{BASE_URL}/projects/{project_id}", headers={
            "Authorization": f"Bearer {access_token}"
        }, timeout=10)
        
        if resp.status_code in [200, 204]:
            return log("删除项目", True, "Cleanup successful")
        else:
            return log("删除项目", False, f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return log("删除项目", False, str(e))


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("墨灵项目 - 全面API自动化测试")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试用户: {TEST_USER['email']}")
    print("=" * 60)
    
    # 按顺序执行测试
    test_01_register()
    test_02_login()
    test_03_get_me()
    test_04_update_profile()
    test_05_create_project()
    test_06_list_projects()
    test_07_get_project()
    test_08_update_project()
    test_09_create_chapter()
    test_10_list_chapters()
    test_11_get_chapter()
    test_12_update_chapter()
    test_13_draw_card()
    test_14_list_cards()
    test_15_create_vault_entry()
    test_16_get_vault()
    test_17_trigger_generation()
    test_18_unauthorized_access()
    test_19_invalid_token()
    test_20_delete_project()
    
    # 生成测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    print(f"总测试数: {passed + failed}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"通过率: {passed/(passed+failed)*100:.1f}%")
    print("=" * 60)
    
    # 保存详细报告
    report = {
        "summary": {
            "total": passed + failed,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed/(passed+failed)*100:.1f}%",
            "timestamp": datetime.now().isoformat()
        },
        "details": test_results
    }
    
    with open("C:/Users/Admin/Desktop/新建文件夹 (2)/api_test_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n详细报告已保存到: api_test_report.json")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
