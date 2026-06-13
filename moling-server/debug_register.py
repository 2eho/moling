"""调试脚本 - 直接测试注册功能"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 添加项目路径
sys.path.insert(0, r"C:\Users\Admin\Desktop\MolingProject\moling-server")

from app.config import get_settings
from app.models.base import Base
from app.service import auth_service
from app.schemas.auth import RegisterReq

async def test_register():
    """直接测试注册功能"""
    settings = get_settings()
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    
    # 创建异步引擎
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    # 创建表（如果不存在）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 创建会话
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # 尝试注册
            req = RegisterReq(
                email="debug_test@example.com",
                nickname="调试测试",
                password="TestPass123!"
            )
            print(f"\n尝试注册用户: {req.email}")
            result = await auth_service.register(session, req)
            print(f"注册成功!")
            print(f"Access Token: {result.access_token[:20]}...")
            print(f"User: {result.user}")
        except Exception as e:
            print(f"\n注册失败: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await session.close()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_register())
