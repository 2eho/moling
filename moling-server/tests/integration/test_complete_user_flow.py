"""补充集成测试 - 完整用户流程。

测试场景：
1. 用户注册 -> 登录 -> 创建项目 -> 查看项目（完整流程）
2. Token 失效测试
3. 项目 CRUD 完整流程
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:
    print("ERROR: requests 库未安装，请运行: pip install requests")
    sys.exit(1)


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

# 测试用户
TEST_USER = {
    "email": "integration_flow@example.com",
    "nickname": "integrationflow",
    "password": "TestPass123!",
}

# 测试项目
TEST_PROJECT = {
    "name": "集成测试流程项目",
    "description": "用于测试完整用户流程的项目",
    "novel_type": "都市",
    "cover_url": "",
}


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def print_section(title: str) -> None:
    """Print a section title."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_test(name: str, passed: bool, detail: str = "") -> None:
    """Print a test result."""
    status = "[PASS]" if passed else "[FAIL]"
    detail_str = f" — {detail}" if detail else ""
    print(f"  {status} {name}{detail_str}")


# ---------------------------------------------------------------------------
# 测试场景
# ---------------------------------------------------------------------------

def test_complete_user_flow() -> Dict[str, Any]:
    """测试完整用户流程：注册 -> 登录 -> 创建项目 -> 查看项目。"""
    print_section("测试场景 1: 完整用户流程")
    
    result = {"scenario": "complete_user_flow", "steps": [], "success": False}
    
    # 1. 用户注册
    print("\n  步骤 1: 用户注册...")
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/register",
            json=TEST_USER,
            timeout=10,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            user = data.get("user", {})
            
            if access_token and user.get("email") == TEST_USER["email"]:
                print("  [PASS] 用户注册成功")
                result["steps"].append({
                    "step": "register",
                    "status": "passed",
                    "detail": f"User ID: {user.get('id')}"
                })
                result["access_token"] = access_token
                result["refresh_token"] = refresh_token
                result["user"] = user
            else:
                print(f"  [FAIL] 用户注册失败 — 响应中缺少令牌或用户信息")
                result["steps"].append({
                    "step": "register",
                    "status": "failed",
                    "detail": "Missing token or user info"
                })
                return result
        elif resp.status_code == 409:
            # 用户已存在，尝试登录获取令牌
            print("  [WARN] 用户已存在，尝试登录...")
            result["steps"].append({
                "step": "register",
                "status": "skipped",
                "detail": "User already exists"
            })
            # 跳转到登录步骤
            pass
        else:
            print(f"  [FAIL] 用户注册失败 — HTTP {resp.status_code}: {resp.text}")
            result["steps"].append({
                "step": "register",
                "status": "failed",
                "detail": f"HTTP {resp.status_code}: {resp.text}"
            })
            return result
    except Exception as e:
        print(f"  [FAIL] 用户注册失败 — {e}")
        result["steps"].append({
            "step": "register",
            "status": "failed",
            "detail": str(e)
        })
        return result
    
    # 如果注册失败但用户已存在，则登录
    if "access_token" not in result:
        print("\n  步骤 2: 用户登录（用户已存在）...")
        try:
            resp = requests.post(
                f"{BASE_URL}{API_PREFIX}/auth/login",
                json={
                    "email": TEST_USER["email"],
                    "password": TEST_USER["password"],
                },
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                access_token = data.get("access_token")
                refresh_token = data.get("refresh_token")
                
                if access_token:
                    print("  [PASS] 用户登录成功")
                    result["steps"].append({
                        "step": "login",
                        "status": "passed",
                        "detail": "Logged in with existing user"
                    })
                    result["access_token"] = access_token
                    result["refresh_token"] = refresh_token
                else:
                    print("  [FAIL] 用户登录失败 — 响应中缺少访问令牌")
                    result["steps"].append({
                        "step": "login",
                        "status": "failed",
                        "detail": "Missing access token"
                    })
                    return result
            else:
                print(f"  [FAIL] 用户登录失败 — HTTP {resp.status_code}: {resp.text}")
                result["steps"].append({
                    "step": "login",
                    "status": "failed",
                    "detail": f"HTTP {resp.status_code}: {resp.text}"
                })
                return result
        except Exception as e:
            print(f"  [FAIL] 用户登录失败 — {e}")
            result["steps"].append({
                "step": "login",
                "status": "failed",
                "detail": str(e)
            })
            return result
    else:
        print("\n  步骤 2: 用户登录（跳过，已通过注册获取令牌）...")
        result["steps"].append({
            "step": "login",
            "status": "skipped",
            "detail": "Token obtained from registration"
        })
    
    # 3. 获取当前用户信息
    print("\n  步骤 3: 获取当前用户信息...")
    headers = {"Authorization": f"Bearer {result['access_token']}"}
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/auth/me",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("email") == TEST_USER["email"]:
                print("  [PASS] 获取当前用户信息成功")
                result["steps"].append({
                    "step": "get_me",
                    "status": "passed",
                    "detail": f"User: {data.get('email')}"
                })
            else:
                print("  [FAIL] 获取当前用户信息失败 — 返回的用户信息不匹配")
                result["steps"].append({
                    "step": "get_me",
                    "status": "failed",
                    "detail": "User info mismatch"
                })
        else:
            print(f"  [FAIL] 获取当前用户信息失败 — HTTP {resp.status_code}: {resp.text}")
            result["steps"].append({
                "step": "get_me",
                "status": "failed",
                "detail": f"HTTP {resp.status_code}: {resp.text}"
            })
    except Exception as e:
        print(f"  [FAIL] 获取当前用户信息失败 — {e}")
        result["steps"].append({
            "step": "get_me",
            "status": "failed",
            "detail": str(e)
        })
    
    # 4. 创建项目
    print("\n  步骤 4: 创建项目...")
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/projects/",
            json=TEST_PROJECT,
            headers=headers,
            timeout=10,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            project_id = data.get("id") or data.get("project_id")
            if project_id:
                print(f"  [PASS] 创建项目成功 — Project ID: {project_id}")
                result["steps"].append({
                    "step": "create_project",
                    "status": "passed",
                    "detail": f"Project ID: {project_id}"
                })
                result["project_id"] = project_id
            else:
                print("  [FAIL] 创建项目失败 — 响应中缺少项目 ID")
                result["steps"].append({
                    "step": "create_project",
                    "status": "failed",
                    "detail": "Missing project ID"
                })
                return result
        else:
            print(f"  [FAIL] 创建项目失败 — HTTP {resp.status_code}: {resp.text}")
            result["steps"].append({
                "step": "create_project",
                "status": "failed",
                "detail": f"HTTP {resp.status_code}: {resp.text}"
            })
            # 项目模块可能未实现，跳过后续步骤
            result["success"] = False
            return result
    except Exception as e:
        print(f"  [FAIL] 创建项目失败 — {e}")
        result["steps"].append({
            "step": "create_project",
            "status": "failed",
            "detail": str(e)
        })
        return result
    
    # 5. 查看项目列表
    print("\n  步骤 5: 查看项目列表...")
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/projects/",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            # 检查列表是否包含创建的项目
            projects = data if isinstance(data, list) else data.get("items", [])
            found = any(p.get("id") == result["project_id"] for p in projects)
            if found:
                print("  [PASS] 查看项目列表成功 — 找到创建的项目")
                result["steps"].append({
                    "step": "list_projects",
                    "status": "passed",
                    "detail": f"Found project {result['project_id']}"
                })
            else:
                print("  [WARN] 查看项目列表 — 项目列表中未找到创建的项目")
                result["steps"].append({
                    "step": "list_projects",
                    "status": "warned",
                    "detail": "Project not found in list"
                })
        else:
            print(f"  [FAIL] 查看项目列表失败 — HTTP {resp.status_code}: {resp.text}")
            result["steps"].append({
                "step": "list_projects",
                "status": "failed",
                "detail": f"HTTP {resp.status_code}: {resp.text}"
            })
    except Exception as e:
        print(f"  [FAIL] 查看项目列表失败 — {e}")
        result["steps"].append({
            "step": "list_projects",
            "status": "failed",
            "detail": str(e)
        })
    
    # 6. 查看项目详情
    print("\n  步骤 6: 查看项目详情...")
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/projects/{result['project_id']}",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("id") == result["project_id"]:
                print("  [PASS] 查看项目详情成功")
                result["steps"].append({
                    "step": "get_project",
                    "status": "passed",
                    "detail": f"Project {result['project_id']} details retrieved"
                })
            else:
                print("  [FAIL] 查看项目详情失败 — 返回的项目 ID 不匹配")
                result["steps"].append({
                    "step": "get_project",
                    "status": "failed",
                    "detail": "Project ID mismatch"
                })
        else:
            print(f"  [FAIL] 查看项目详情失败 — HTTP {resp.status_code}: {resp.text}")
            result["steps"].append({
                "step": "get_project",
                "status": "failed",
                "detail": f"HTTP {resp.status_code}: {resp.text}"
            })
    except Exception as e:
        print(f"  [FAIL] 查看项目详情失败 — {e}")
        result["steps"].append({
            "step": "get_project",
            "status": "failed",
            "detail": str(e)
        })
    
    # 7. 刷新 Token
    print("\n  步骤 7: 刷新 Token...")
    try:
        resp = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/refresh",
            json={"refresh_token": result["refresh_token"]},
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            new_access = data.get("access_token")
            if new_access:
                print("  [PASS] 刷新 Token 成功")
                result["steps"].append({
                    "step": "refresh_token",
                    "status": "passed",
                    "detail": "New access token obtained"
                })
                # 更新令牌
                result["access_token"] = new_access
                headers["Authorization"] = f"Bearer {new_access}"
            else:
                print("  [FAIL] 刷新 Token 失败 — 响应中缺少新的访问令牌")
                result["steps"].append({
                    "step": "refresh_token",
                    "status": "failed",
                    "detail": "Missing new access token"
                })
        else:
            print(f"  [FAIL] 刷新 Token 失败 — HTTP {resp.status_code}: {resp.text}")
            result["steps"].append({
                "step": "refresh_token",
                "status": "failed",
                "detail": f"HTTP {resp.status_code}: {resp.text}"
            })
    except Exception as e:
        print(f"  [FAIL] 刷新 Token 失败 — {e}")
        result["steps"].append({
            "step": "refresh_token",
            "status": "failed",
            "detail": str(e)
        })
    
    # 8. 使用新 Token 访问受保护端点
    print("\n  步骤 8: 使用刷新后的 Token 访问受保护端点...")
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/auth/me",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            print("  [PASS] 使用刷新后的 Token 访问受保护端点成功")
            result["steps"].append({
                "step": "access_with_new_token",
                "status": "passed",
                "detail": "New token works"
            })
        else:
            print(f"  [FAIL] 使用刷新后的 Token 访问受保护端点失败 — HTTP {resp.status_code}: {resp.text}")
            result["steps"].append({
                "step": "access_with_new_token",
                "status": "failed",
                "detail": f"HTTP {resp.status_code}: {resp.text}"
            })
    except Exception as e:
        print(f"  [FAIL] 使用刷新后的 Token 访问受保护端点失败 — {e}")
        result["steps"].append({
            "step": "access_with_new_token",
            "status": "failed",
            "detail": str(e)
        })
    
    # 计算成功率
    passed_steps = sum(1 for s in result["steps"] if s["status"] == "passed")
    total_steps = len(result["steps"])
    success_rate = (passed_steps / total_steps * 100) if total_steps > 0 else 0
    
    print(f"\n  场景 1 完成: {passed_steps}/{total_steps} 步骤通过 ({success_rate:.1f}%)")
    result["success"] = success_rate == 100
    result["success_rate"] = success_rate
    
    return result


def test_token_invalidation() -> Dict[str, Any]:
    """测试 Token 失效场景。"""
    print_section("测试场景 2: Token 失效测试")
    
    result = {"scenario": "token_invalidation", "steps": [], "success": False}
    
    # 1. 使用无效 Token 访问受保护端点
    print("\n  步骤 1: 使用无效 Token 访问受保护端点...")
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
            timeout=10,
        )
        if resp.status_code in (401, 403):
            print("  [PASS] 无效 Token 正确返回 401/403")
            result["steps"].append({
                "step": "invalid_token",
                "status": "passed",
                "detail": f"HTTP {resp.status_code}"
            })
        else:
            print(f"  [FAIL] 无效 Token 应该返回 401/403，实际返回 {resp.status_code}")
            result["steps"].append({
                "step": "invalid_token",
                "status": "failed",
                "detail": f"Expected 401/403, got {resp.status_code}"
            })
    except Exception as e:
        print(f"  [FAIL] 无效 Token 测试失败 — {e}")
        result["steps"].append({
            "step": "invalid_token",
            "status": "failed",
            "detail": str(e)
        })
    
    # 2. 不提供 Token 访问受保护端点
    print("\n  步骤 2: 不提供 Token 访问受保护端点...")
    try:
        resp = requests.get(
            f"{BASE_URL}{API_PREFIX}/auth/me",
            timeout=10,
        )
        if resp.status_code in (401, 403):
            print("  [PASS] 无 Token 正确返回 401/403")
            result["steps"].append({
                "step": "no_token",
                "status": "passed",
                "detail": f"HTTP {resp.status_code}"
            })
        else:
            print(f"  [FAIL] 无 Token 应该返回 401/403，实际返回 {resp.status_code}")
            result["steps"].append({
                "step": "no_token",
                "status": "failed",
                "detail": f"Expected 401/403, got {resp.status_code}"
            })
    except Exception as e:
        print(f"  [FAIL] 无 Token 测试失败 — {e}")
        result["steps"].append({
            "step": "no_token",
            "status": "failed",
            "detail": str(e)
        })
    
    # 计算成功率
    passed_steps = sum(1 for s in result["steps"] if s["status"] == "passed")
    total_steps = len(result["steps"])
    success_rate = (passed_steps / total_steps * 100) if total_steps > 0 else 0
    
    print(f"\n  场景 2 完成: {passed_steps}/{total_steps} 步骤通过 ({success_rate:.1f}%)")
    result["success"] = success_rate == 100
    result["success_rate"] = success_rate
    
    return result


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def main() -> None:
    """运行所有补充集成测试。"""
    print("=" * 60)
    print("  墨灵 (Moling) 补充集成测试")
    print("=" * 60)
    
    # 等待后端启动
    print("\n等待后端服务启动...")
    max_retries = 10
    for i in range(max_retries):
        try:
            resp = requests.get(f"{BASE_URL}{API_PREFIX}/health", timeout=5)
            if resp.status_code == 200:
                print("  [OK] 后端服务已启动")
                break
        except requests.exceptions.ConnectionError:
            if i < max_retries - 1:
                print(f"  重试 {i + 1}/{max_retries}...")
                time.sleep(2)
            else:
                print("  [FAIL] 后端服务未启动，请先启动后端服务")
                print("   启动命令: cd moling-server && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
                sys.exit(1)
    
    # 运行测试场景
    results = []
    
    # 场景 1: 完整用户流程
    result1 = test_complete_user_flow()
    results.append(result1)
    
    # 场景 2: Token 失效测试
    result2 = test_token_invalidation()
    results.append(result2)
    
    # 生成报告
    print("\n" + "=" * 60)
    print("  测试报告")
    print("=" * 60)
    
    total_scenarios = len(results)
    passed_scenarios = sum(1 for r in results if r["success"])
    
    print(f"\n总计: {total_scenarios} 个测试场景")
    print(f"  通过: {passed_scenarios}")
    print(f"  失败: {total_scenarios - passed_scenarios}")
    
    # 保存报告
    report_path = "tests/integration/SUPPLEMENTARY_TEST_REPORT.md"
    print(f"\n报告已保存到: {report_path}")
    
    # 生成 Markdown 报告
    generate_markdown_report(results, report_path)
    
    # 返回退出码
    sys.exit(0 if passed_scenarios == total_scenarios else 1)


def generate_markdown_report(results: list[Dict[str, Any]], path: str) -> None:
    """生成 Markdown 格式的测试报告。"""
    from pathlib import Path
    
    # 确保目录存在
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    
    lines = [
        "# 墨灵 (Moling) 补充集成测试报告",
        "",
        f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 摘要",
        "",
    ]
    
    total_scenarios = len(results)
    passed_scenarios = sum(1 for r in results if r["success"])
    
    lines.extend([
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 总测试场景数 | {total_scenarios} |",
        f"| 通过 | {passed_scenarios} |",
        f"| 失败 | {total_scenarios - passed_scenarios} |",
        "",
        "## 测试场景结果",
        "",
    ])
    
    for result in results:
        scenario = result["scenario"]
        success = result["success"]
        success_rate = result.get("success_rate", 0)
        
        status_str = "✅ 通过" if success else "❌ 失败"
        lines.append(f"### {status_str} — {scenario} (成功率: {success_rate:.1f}%)")
        lines.append("")
        
        for step in result.get("steps", []):
            step_name = step["step"]
            step_status = step["status"]
            step_detail = step.get("detail", "")
            
            if step_status == "passed":
                lines.append(f"- ✅ **{step_name}**: {step_detail}")
            elif step_status == "failed":
                lines.append(f"- ❌ **{step_name}**: {step_detail}")
            elif step_status == "warned":
                lines.append(f"- ⚠️ **{step_name}**: {step_detail}")
            elif step_status == "skipped":
                lines.append(f"- ⏭ **{step_name}**: {step_detail}")
        
        lines.append("")
    
    lines.extend([
        "## 测试环境信息",
        "",
        f"- 后端 URL: {BASE_URL}",
        f"- API 前缀: {API_PREFIX}",
        f"- 测试用户: {TEST_USER['email']}",
        "",
    ])
    
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
