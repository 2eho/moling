"""
数据库迁移回滚测试脚本

功能：
1. 升级到最新版本
2. 回滚一个版本
3. 再次升级到最新版本
4. 验证数据完整性

使用方法：
    python scripts/test_rollback.py [--db-url DATABASE_URL]

环境变量：
    DATABASE_URL: 数据库连接URL（可选，默认使用 .env 中的配置）
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 加载 .env 文件
_dotenv_path = PROJECT_ROOT / ".env"
if _dotenv_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_dotenv_path)
    except ImportError:
        pass

import alembic
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def get_alembic_config(db_url: str | None = None) -> Config:
    """创建 Alembic 配置"""
    config = Config(PROJECT_ROOT / "alembic.ini")

    # 设置数据库 URL
    if db_url is None:
        db_url = os.environ.get("DATABASE_URL", "sqlite:///./moling.db")

    # 转换 async URL 为 sync URL（Alembic 需要同步引擎）
    if db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    elif db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    config.set_main_option("sqlalchemy.url", db_url)
    return config


def get_current_revision(config: Config) -> str | None:
    """获取当前数据库版本"""
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import engine_from_config

    # 创建引擎
    engine = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=__import__("sqlalchemy.pool").pool.NullPool,
    )

    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        current_rev = context.get_current_revision()

    engine.dispose()
    return current_rev


def test_rollback(db_url: str | None = None, verbose: bool = True):
    """
    测试数据库迁移回滚

    流程：
    1. 升级到最新版本 (head)
    2. 回滚一个版本 (-1)
    3. 再次升级到最新版本 (head)
    4. 验证数据完整性
    """
    config = get_alembic_config(db_url)
    log = print if verbose else lambda *a, **k: None

    log("=" * 60)
    log("数据库迁移回滚测试")
    log("=" * 60)

    try:
        # 步骤 1: 升级到最新版本
        log("\n[步骤 1] 升级到最新版本 (head)...")
        start_time = time.time()
        command.upgrade(config, "head")
        elapsed = time.time() - start_time
        log(f"✓ 升级完成 ({elapsed:.2f}s)")

        # 获取当前版本
        current_rev = get_current_revision(config)
        log(f"  当前版本: {current_rev}")

        # 步骤 2: 回滚一个版本
        log("\n[步骤 2] 回滚一个版本 (-1)...")
        start_time = time.time()
        command.downgrade(config, "-1")
        elapsed = time.time() - start_time
        log(f"✓ 回滚完成 ({elapsed:.2f}s)")

        # 获取回滚后的版本
        after_downgrade_rev = get_current_revision(config)
        log(f"  回滚后版本: {after_downgrade_rev}")

        # 步骤 3: 再次升级到最新版本
        log("\n[步骤 3] 再次升级到最新版本 (head)...")
        start_time = time.time()
        command.upgrade(config, "head")
        elapsed = time.time() - start_time
        log(f"✓ 升级完成 ({elapsed:.2f}s)")

        # 获取最终版本
        final_rev = get_current_revision(config)
        log(f"  最终版本: {final_rev}")

        # 步骤 4: 验证数据完整性
        log("\n[步骤 4] 验证数据完整性...")
        verify_data_integrity(config, log)

        log("\n" + "=" * 60)
        log("✓ 所有测试通过！")
        log("=" * 60)
        return True

    except Exception as e:
        log(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_data_integrity(config: Config, log=print):
    """
    验证数据完整性

    检查：
    1. 所有表都存在
    2. 基本查询可以执行
    """
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import engine_from_config

    # 创建引擎
    engine = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=__import__("sqlalchemy.pool").pool.NullPool,
    )

    try:
        with engine.connect() as conn:
            # 获取所有表
            from app.models import Base
            tables = Base.metadata.tables.keys()

            log(f"  检查 {len(tables)} 个表...")

            for table_name in tables:
                # 检查表是否存在并可以查询
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    log(f"    ✓ {table_name}: {count} 行")
                except Exception as e:
                    log(f"    ✗ {table_name}: {e}")
                    raise

            log("  ✓ 数据完整性验证通过")

    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="数据库迁移回滚测试")
    parser.add_argument(
        "--db-url",
        help="数据库连接 URL (默认: 使用 .env 中的 DATABASE_URL)",
        default=None,
    )
    parser.add_argument(
        "--quiet",
        help="静默模式",
        action="store_true",
    )

    args = parser.parse_args()

    success = test_rollback(
        db_url=args.db_url,
        verbose=not args.quiet,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
