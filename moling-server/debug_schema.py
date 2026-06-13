"""调试脚本 - 测试 schema 验证"""
import sys
from datetime import datetime

sys.path.insert(0, r"C:\Users\Admin\Desktop\MolingProject\moling-server")

from app.schemas.auth import UserResp, TokenResp, RegisterReq
from pydantic import ValidationError

# 测试 UserResp schema
print("测试 UserResp schema...")
try:
    user_data = {
        "id": "1",  # 字符串 ID
        "email": "test@example.com",
        "nickname": "测试用户",  # 应该使用 username 作为别名
        "avatar_url": None,
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    user_resp = UserResp(**user_data)
    print(f"  UserResp 创建成功: {user_resp}")
except ValidationError as e:
    print(f"  UserResp 验证失败: {e}")
except Exception as e:
    print(f"  UserResp 创建失败: {type(e).__name__}: {e}")

# 测试 TokenResp schema
print("\n测试 TokenResp schema...")
try:
    token_data = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "user": {
            "id": "1",
            "email": "test@example.com",
            "nickname": "测试用户",
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    }
    token_resp = TokenResp(**token_data)
    print(f"  TokenResp 创建成功: {token_resp}")
except ValidationError as e:
    print(f"  TokenResp 验证失败: {e}")
except Exception as e:
    print(f"  TokenResp 创建失败: {type(e).__name__}: {e}")

# 测试 RegisterReq schema
print("\n测试 RegisterReq schema...")
try:
    req_data = {
        "email": "test@example.com",
        "nickname": "测试用户",
        "password": "TestPass123!"
    }
    req = RegisterReq(**req_data)
    print(f"  RegisterReq 创建成功: {req}")
except ValidationError as e:
    print(f"  RegisterReq 验证失败: {e}")
except Exception as e:
    print(f"  RegisterReq 创建失败: {type(e).__name__}: {e}")

print("\n完成")
