#!/usr/bin/env python3
# test-integration.py — 墨灵 API 集成测试
import json, sys, urllib.request, urllib.error

BASE = "http://localhost:8001/api/v1"

def post(path, body, headers=None):
    data = json.dumps(body).encode("utf-8")
    h = {"Content-Type": "application/json"}
    if headers: h.update(headers)
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{BASE}{path}", data, h, method="POST"), timeout=10) as r:
            return {"http_status": r.status, **json.loads(r.read())}
    except urllib.error.HTTPError as e:
        return {"http_status": e.code, **json.loads(e.read())}

def get(path, token=None):
    h = {}
    if token: h["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{BASE}{path}", headers=h), timeout=10) as r:
            return {"http_status": r.status, **json.loads(r.read())}
    except urllib.error.HTTPError as e:
        return {"http_status": e.code, **json.loads(e.read())}

def check(r, label, expect=(200, 201)):
    ok = r["http_status"] in expect
    info = f"  {r['http_status']}"
    if not ok:
        info += f"  FAIL: {json.dumps(r, ensure_ascii=False)[:120]}"
    print(f"{label} {info}")
    return ok

def main():
    fails = 0

    # 1. 注册
    r = post("/auth/register", {"email": "t_api_01@moling.com", "password": "Test@123456", "nickname": "API测试"})
    if not check(r, "=== 1. 注册 ===", expect=(200, 201, 400)):
        fails += 1; sys.exit(1)

    # 2. 登录
    r = post("/auth/login", {"email": "t_api_01@moling.com", "password": "Test@123456"})
    if not check(r, "=== 2. 登录 ===", expect=(200,)):
        fails += 1; sys.exit(1)
    token = r.get("access_token")
    print(f"    Token: {token[:20]}..." if token else "    FAIL: no token")

    # 3. 获取用户信息
    r = get("/auth/me", token=token)
    if not check(r, "=== 3. 获取用户信息 ===", expect=(200,)): fails += 1
    else: print(f"    {r.get('nickname')} <{r.get('email')}>")

    # 4. 创建项目
    r = post("/projects", {"title": "Test Novel", "author": "API Tester", "description": "A test project", "genre": "fantasy"},
               {"Authorization": f"Bearer {token}"})
    if not check(r, "=== 4. 创建项目 ===", expect=(200, 201)): fails += 1
    else:
        pid = r.get("id")
        print(f"    Project id: {pid}")

        # 5. 项目详情
        r = get(f"/projects/{pid}", token=token)
        check(r, "=== 5. 项目详情 ===")

        # 6. 四库-角色
        r = get(f"/vault/characters?project_id={pid}", token=token)
        check(r, "=== 6. 四库-角色 ===")

        # 7. 四库-时间线
        r = get(f"/vault/timeline?project_id={pid}", token=token)
        check(r, "=== 7. 四库-时间线 ===")

        # 8. 健康检查
        r = get(f"/projects/{pid}/health", token=token)
        check(r, "=== 8. 健康检查 ===")

        # 9. 获取模板
        r = get("/templates", token=token)
        check(r, "=== 9. 获取模板 ===")

        # 10. Vault Summary
        r = get(f"/vault/summary?project_id={pid}", token=token)
        check(r, "=== 10. Vault Summary ===")

    # 11. Settings
    r = get("/settings", token=token)
    check(r, "=== 11. Settings ===")

    # 12. Notifications
    r = get("/notifications", token=token)
    check(r, "=== 12. Notifications ===")

    # 13. 系统健康检查（无需 token）
    r = get("/health")
    check(r, "=== 13. 系统健康检查 ===")

    print(f"\n=== 测试完成 ===  Fails: {fails}")

if __name__ == "__main__":
    main()
