"""排查性能测试失败原因."""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_login():
    """测试登录功能."""
    print("="*60)
    print("测试1: 登录功能")
    print("="*60)
    
    # 尝试登录
    data = {
        "email": "test1@moling.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=data, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:500]}")
        
        if response.status_code == 200:
            result = response.json()
            # 检查响应格式
            if "data" in result and "access_token" in result["data"]:
                token = result["data"]["access_token"]
                print(f"✅ 登录成功，获取到token: {token[:20]}...")
                return token
            else:
                print(f"❌ 响应格式错误: {result}")
                return None
        else:
            print(f"❌ 登录失败")
            return None
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None

def test_register():
    """测试注册功能."""
    print("\n" + "="*60)
    print("测试2: 注册功能")
    print("="*60)
    
    import random
    data = {
        "email": f"perftest_{random.randint(1000, 9999)}@moling.com",
        "nickname": "性能测试用户",
        "password": "Password123!"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=data, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:500]}")
        
        if response.status_code in (200, 201):
            print("✅ 注册成功")
            return True
        else:
            print("❌ 注册失败")
            return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def test_list_projects(token):
    """测试获取项目列表."""
    print("\n" + "="*60)
    print("测试3: 获取项目列表")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/projects", headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:500]}")
        
        if response.status_code == 200:
            print("✅ 获取项目列表成功")
            return True
        else:
            print("❌ 获取项目列表失败")
            return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def test_create_project(token):
    """测试创建项目."""
    print("\n" + "="*60)
    print("测试4: 创建项目")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "title": "性能测试项目",
        "author": "测试作者",
        "genre": "玄幻",
        "creation_mode": "from_scratch",
        "status": "draft"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/projects", json=data, headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:500]}")
        
        if response.status_code in (200, 201):
            print("✅ 创建项目成功")
            return True
        else:
            print("❌ 创建项目失败")
            return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def check_backend_health():
    """检查后端健康状态."""
    print("="*60)
    print("检查后端健康状态")
    print("="*60)
    
    # 尝试访问docs端点
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ 后端服务正在运行 (/docs 可访问)")
        else:
            print(f"⚠️  /docs 返回状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接到后端: {e}")
        return False
    
    # 尝试访问openapi.json
    try:
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        if response.status_code == 200:
            print("✅ OpenAPI文档可访问")
            # 检查API端点是否存在
            openapi = response.json()
            paths = openapi.get("paths", {})
            print(f"   发现的API端点数量: {len(paths)}")
            for path in list(paths.keys())[:10]:
                print(f"   - {path}")
        else:
            print(f"⚠️  /openapi.json 返回状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 无法访问OpenAPI文档: {e}")
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("墨灵后端API排查工具")
    print("="*60)
    
    # 检查后端健康状态
    if not check_backend_health():
        print("\n❌ 后端服务未运行，请先启动后端服务")
        sys.exit(1)
    
    # 测试注册
    test_register()
    
    # 测试登录
    token = test_login()
    
    if token:
        # 测试获取项目列表
        test_list_projects(token)
        
        # 测试创建项目
        test_create_project(token)
    else:
        print("\n⚠️  无法获取token，跳过需要认证的测试")
    
    print("\n" + "="*60)
    print("排查完成")
    print("="*60)
