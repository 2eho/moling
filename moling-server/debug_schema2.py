"""调试脚本 - 测试 User 模型到 UserResp 的转换"""
import sys
from datetime import datetime
from unittest.mock import MagicMock

sys.path.insert(0, r"C:\Users\Admin\Desktop\MolingProject\moling-server")

from app.schemas.auth import UserResp
from pydantic import ValidationError

# 模拟 User ORM 对象
print("测试 User ORM -> UserResp 转换...")
try:
    # 创建一个模拟的 User 对象
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.username = "测试用户"  # User 模型有 username 字段
    mock_user.avatar_url = None
    mock_user.status = "active"
    mock_user.created_at = datetime.now()
    mock_user.updated_at = datetime.now()
    
    # 尝试转换
    user_resp = UserResp.model_validate(mock_user)
    print(f"  成功: {user_resp}")
    print(f"  nickname: {user_resp.nickname}")
except ValidationError as e:
    print(f"  验证失败: {e}")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")

# 测试使用字典输入（使用 username 作为键）
print("\n测试字典输入（使用 username）...")
try:
    user_data = {
        "id": "1",
        "email": "test@example.com",
        "username": "测试用户",  # 使用 validation_alias
        "avatar_url": None,
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    user_resp = UserResp(**user_data)
    print(f"  成功: {user_resp}")
except ValidationError as e:
    print(f"  验证失败: {e}")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")

print("\n完成")
