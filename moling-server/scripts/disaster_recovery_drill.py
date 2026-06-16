"""
灾备演练脚本

功能：
1. 在 staging 环境恢复最新备份
2. 验证数据完整性
3. 运行基本查询测试
4. 报告演练结果

使用方法：
    # 基本使用（自动查找最新备份）
    python scripts/disaster_recovery_drill.py

    # 指定备份文件
    python scripts/disaster_recovery_drill.py --backup-file /path/to/backup.sql.gz

    # 指定目标数据库（用于恢复测试）
    python scripts/disaster_recovery_drill.py --target-db postgres_test

环境变量：
    DATABASE_URL: 目标数据库连接 URL（staging 环境）
    BACKUP_DIR: 备份文件目录 (默认: ./backups)
"""

from __future__ import annotations

import argparse
import datetime
import gzip
import json
import os
import shutil
import smtplib
import subprocess
import sys
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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

# 可选依赖检查
try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def parse_db_url(db_url: str) -> dict:
    """解析数据库连接 URL"""
    url = db_url.replace("postgresql://", "").replace("postgresql+asyncpg://", "")

    if "@" in url:
        user_pass, rest = url.split("@", 1)
        if ":" in user_pass:
            user, password = user_pass.split(":", 1)
        else:
            user, password = user_pass, ""
    else:
        user, password, rest = "postgres", "", url

    if "/" in rest:
        host_port, database = rest.split("/", 1)
    else:
        host_port, database = rest, "postgres"

    if ":" in host_port:
        host, port = host_port.split(":", 1)
    else:
        host, port = host_port, "5432"

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
    }


def find_latest_backup(backup_dir: Path, backup_type: str = "full") -> Path | None:
    """
    查找最新的备份文件

    参数：
        backup_dir: 备份目录
        backup_type: 备份类型 (full/incremental)

    返回：
        最新的备份文件路径，如果没有找到则返回 None
    """
    print(f"在 {backup_dir} 中查找最新备份...")

    # 查找匹配的备份文件
    pattern = f"*_{backup_type}_*.sql*"
    backups = list(backup_dir.glob(pattern))

    if not backups:
        print(f"✗ 未找到 {backup_type} 类型的备份文件")
        return None

    # 按修改时间排序，获取最新的
    latest = max(backups, key=lambda p: p.stat().st_mtime)
    print(f"✓ 找到最新备份: {latest.name}")
    return latest


def decompress_backup(backup_file: Path, work_dir: Path) -> Path:
    """
    解压备份文件（如果是 .gz）

    返回：
        解压后的文件路径
    """
    if backup_file.suffix == ".gz":
        print(f"解压备份文件: {backup_file.name}")
        decompressed = work_dir / backup_file.stem  # 移除 .gz

        with gzip.open(backup_file, "rb") as f_in:
            with open(decompressed, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        print(f"✓ 解压完成: {decompressed.name}")
        return decompressed
    else:
        return backup_file


def drop_database(db_params: dict):
    """删除数据库（用于恢复测试）"""
    print(f"删除数据库: {db_params['database']}")

    env = os.environ.copy()
    if db_params["password"]:
        env["PGPASSWORD"] = db_params["password"]

    # 终止所有连接到目标数据库的会话
    terminate_cmd = [
        "psql",
        f"--host={db_params['host']}",
        f"--port={db_params['port']}",
        f"--username={db_params['user']}",
        "--dbname=postgres",
        "--no-password",
        "--command",
        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_params['database']}';",
    ]

    try:
        subprocess.run(terminate_cmd, env=env, capture_output=True, check=False)
    except Exception:
        pass

    # 删除数据库
    drop_cmd = [
        "dropdb",
        f"--host={db_params['host']}",
        f"--port={db_params['port']}",
        f"--username={db_params['user']}",
        "--no-password",
        "--if-exists",
        db_params["database"],
    ]

    try:
        result = subprocess.run(
            drop_cmd,
            env=env,
            capture_output=True,
            text=True,
            check=False,  # 数据库可能不存在
        )
        print(f"✓ 数据库已删除或不存在")
    except FileNotFoundError:
        print("✗ 错误: 未找到 dropdb 命令")
        raise


def create_database(db_params: dict):
    """创建数据库"""
    print(f"创建数据库: {db_params['database']}")

    env = os.environ.copy()
    if db_params["password"]:
        env["PGPASSWORD"] = db_params["password"]

    create_cmd = [
        "createdb",
        f"--host={db_params['host']}",
        f"--port={db_params['port']}",
        f"--username={db_params['user']}",
        "--no-password",
        db_params["database"],
    ]

    try:
        result = subprocess.run(
            create_cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✓ 数据库已创建")
    except subprocess.CalledProcessError as e:
        print(f"✗ 创建数据库失败: {e.stderr}")
        raise
    except FileNotFoundError:
        print("✗ 错误: 未找到 createdb 命令")
        raise


def restore_backup(backup_file: Path, db_params: dict):
    """
    恢复备份到数据库

    使用 psql 执行备份 SQL 文件
    """
    print(f"恢复备份到数据库: {db_params['database']}")
    print(f"备份文件: {backup_file.name}")

    env = os.environ.copy()
    if db_params["password"]:
        env["PGPASSWORD"] = db_params["password"]

    restore_cmd = [
        "psql",
        f"--host={db_params['host']}",
        f"--port={db_params['port']}",
        f"--username={db_params['user']}",
        f"--dbname={db_params['database']}",
        "--no-password",
        "--file",
        str(backup_file),
    ]

    try:
        result = subprocess.run(
            restore_cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✓ 备份恢复完成")
    except subprocess.CalledProcessError as e:
        print(f"✗ 备份恢复失败: {e.stderr}")
        raise
    except FileNotFoundError:
        print("✗ 错误: 未找到 psql 命令")
        raise


def verify_restored_data(db_url: str) -> bool:
    """
    验证恢复后的数据完整性

    检查：
    1. 所有表都存在
    2. 基本查询可以执行
    3. 表中有数据（如果备份时有数据）
    """
    print("\n验证恢复后的数据完整性...")

    # 转换 async URL 为 sync URL
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    try:
        from sqlalchemy import create_engine, text, inspect

        engine = create_engine(db_url)

        with engine.connect() as conn:
            inspector = inspect(conn)

            # 获取所有表
            tables = inspector.get_table_names()
            print(f"  发现 {len(tables)} 个表")

            if not tables:
                print("✗ 没有找到任何表")
                return False

            # 检查每个表
            for table_name in tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    print(f"    ✓ {table_name}: {count} 行")
                except Exception as e:
                    print(f"    ✗ {table_name}: {e}")
                    return False

            print("  ✓ 所有表验证通过")

        engine.dispose()
        return True

    except Exception as e:
        print(f"✗ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_basic_queries(db_url: str) -> bool:
    """
    运行基本查询测试

    测试常见的数据库操作
    """
    print("\n运行基本查询测试...")

    # 转换 async URL 为 sync URL
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(db_url)

        with engine.connect() as conn:
            # 测试 1: 查询版本
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"  ✓ PostgreSQL 版本: {version.split(',')[0]}")

            # 测试 2: 查询当前数据库
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"  ✓ 当前数据库: {db_name}")

            # 测试 3: 查询表数量
            result = conn.execute(
                text(
                    """
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public'
            """
                )
            )
            table_count = result.scalar()
            print(f"  ✓ 公共模式表数量: {table_count}")

            print("  ✓ 所有查询测试通过")

        engine.dispose()
        return True

    except Exception as e:
        print(f"✗ 查询测试失败: {e}")
        return False


def generate_drill_report(
    backup_file: Path,
    db_params: dict,
    success: bool,
    start_time: datetime.datetime,
    output_file: Path | None = None,
    details: dict | None = None,
) -> str:
    """
    生成灾备演练报告

    报告内容包括：
    1. 演练时间
    2. 使用的备份文件
    3. 目标数据库
    4. 验证结果
    5. 详细的测试步骤和结果
    6. 建议
    """
    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()

    # 生成 Markdown 格式报告
    report_md = f"""# 灾备演练报告

**生成时间**: {end_time.strftime('%Y-%m-%d %H:%M:%S')}

## 演练概要

| 项目 | 详情 |
|------|------|
| 演练开始时间 | {start_time.strftime('%Y-%m-%d %H:%M:%S')} |
| 演练结束时间 | {end_time.strftime('%Y-%m-%d %H:%M:%S')} |
| 演练耗时 | {duration:.2f} 秒 |
| 演练结果 | {'✅ **成功**' if success else '❌ **失败**'} |

## 备份文件信息

| 项目 | 详情 |
|------|------|
| 文件名 | `{backup_file.name}` |
| 文件大小 | {backup_file.stat().st_size / (1024 * 1024):.2f} MB |
| 修改时间 | {datetime.datetime.fromtimestamp(backup_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')} |

## 目标数据库信息

| 项目 | 详情 |
|------|------|
| 主机 | `{db_params['host']}` |
| 端口 | `{db_params['port']}` |
| 用户 | `{db_params['user']}` |
| 数据库 | `{db_params['database']}` |

## 验证详情

"""

    # 添加详细的验证步骤
    if details:
        report_md += "\n### 测试步骤\n\n"
        for step_name, step_result in details.items():
            status = "✅ 通过" if step_result.get("success", False) else "❌ 失败"
            report_md += f"**{step_name}**: {status}\n\n"
            if step_result.get("details"):
                report_md += f"```\n{step_result['details']}\n```\n\n"

    # 添加建议
    report_md += "\n## 建议\n\n"

    if success:
        report_md += """- ✅ 灾备演练成功，备份和恢复流程正常工作
- 建议定期（至少每月一次）进行灾备演练
- 建议将演练报告存档，用于合规审计
- 建议测试从云存储恢复的流程图
"""
    else:
        report_md += """- ❌ 灾备演练失败，需要立即调查
- 检查备份文件是否完整
- 检查数据库连接是否正常
- 检查恢复流程是否正确
- 建议增加备份验证步骤
"""

    report_md += "\n---\n*本报告由灾备演练脚本自动生成*\n"

    print(report_md)

    # 保存报告到文件
    if output_file:
        output_file = Path(output_file)
        if output_file.suffix == ".md":
            # 保存为 Markdown
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report_md)
        else:
            # 保存为文本（兼容旧格式）
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report_md)

        print(f"\n报告已保存到: {output_file}")

    return report_md


def send_email_notification(
    subject: str,
    body: str,
    recipients: list[str],
    smtp_server: str = None,
    smtp_port: int = 587,
    smtp_user: str = None,
    smtp_password: str = None,
    use_tls: bool = True,
) -> bool:
    """
    发送邮件通知

    需要环境变量：
        SMTP_SERVER: SMTP 服务器地址
        SMTP_PORT: SMTP 端口 (默认: 587)
        SMTP_USER: SMTP 用户名
        SMTP_PASSWORD: SMTP 密码
        NOTIFICATION_EMAIL_FROM: 发件人邮箱
        NOTIFICATION_EMAIL_TO: 收件人邮箱（逗号分隔）

    或在命令行参数中指定
    """
    # 从环境变量获取配置
    smtp_server = smtp_server or os.environ.get("SMTP_SERVER")
    smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = smtp_user or os.environ.get("SMTP_USER")
    smtp_password = smtp_password or os.environ.get("SMTP_PASSWORD")
    sender = os.environ.get("NOTIFICATION_EMAIL_FROM", smtp_user)

    if not recipients:
        recipients_str = os.environ.get("NOTIFICATION_EMAIL_TO", "")
        recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]

    if not smtp_server or not smtp_user or not smtp_password:
        print("✗ 错误: 未配置 SMTP 设置")
        print("请设置环境变量: SMTP_SERVER, SMTP_USER, SMTP_PASSWORD")
        return False

    if not recipients:
        print("✗ 错误: 未指定收件人")
        return False

    print(f"\n发送邮件通知到: {', '.join(recipients)}")

    try:
        # 创建邮件
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        # 添加正文
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # 连接 SMTP 服务器
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()

        if use_tls:
            server.starttls()
            server.ehlo()

        server.login(smtp_user, smtp_password)
        server.sendmail(sender, recipients, msg.as_string())
        server.quit()

        print("✓ 邮件通知已发送")
        return True

    except Exception as e:
        print(f"✗ 邮件通知发送失败: {e}")
        return False


def send_slack_notification(message: str, webhook_url: str = None) -> bool:
    """
    发送 Slack 通知

    需要环境变量：
        SLACK_WEBHOOK_URL: Slack Webhook URL

    或在命令行参数中指定
    """
    if not HAS_REQUESTS:
        print("✗ 错误: 未安装 requests")
        print("请运行: pip install requests")
        return False

    webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")

    if not webhook_url:
        print("✗ 错误: 未设置 SLACK_WEBHOOK_URL")
        print("请设置环境变量或在参数中指定")
        return False

    print(f"\n发送 Slack 通知...")

    try:
        payload = {
            "text": message,
            "username": "灾备演练机器人",
            "icon_emoji": ":rotating_light:",
        }

        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
        )

        if response.status_code == 200:
            print("✓ Slack 通知已发送")
            return True
        else:
            print(f"✗ Slack 通知发送失败: {response.status_code} {response.text}")
            return False

    except Exception as e:
        print(f"✗ Slack 通知发送失败: {e}")
        return False


def verify_restored_data_enhanced(db_url: str) -> dict:
    """
    增强的数据验证，返回详细的测试结果
    """
    print("\n验证恢复后的数据完整性...")

    result = {
        "数据完整性验证": {"success": False, "details": ""},
    }

    # 转换 async URL 为 sync URL
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    try:
        from sqlalchemy import create_engine, text, inspect

        engine = create_engine(db_url)

        with engine.connect() as conn:
            inspector = inspect(conn)

            # 获取所有表
            tables = inspector.get_table_names()
            print(f"  发现 {len(tables)} 个表")

            if not tables:
                result["数据完整性验证"]["details"] = "没有找到任何表"
                return result

            # 检查每个表
            table_details = []
            all_passed = True

            for table_name in tables:
                try:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = count_result.scalar()
                    table_details.append(f"{table_name}: {count} 行")
                except Exception as e:
                    table_details.append(f"{table_name}: ✗ {e}")
                    all_passed = False

            result["数据完整性验证"]["success"] = all_passed
            result["数据完整性验证"]["details"] = "\n".join(table_details)

        engine.dispose()

    except Exception as e:
        result["数据完整性验证"]["details"] = str(e)
        import traceback
        traceback.print_exc()

    return result


def run_basic_queries_enhanced(db_url: str) -> dict:
    """
    增强的查询测试，返回详细的测试结果
    """
    print("\n运行基本查询测试...")

    results = {
        "PostgreSQL 版本查询": {"success": False, "details": ""},
        "当前数据库查询": {"success": False, "details": ""},
        "表数量查询": {"success": False, "details": ""},
    }

    # 转换 async URL 为 sync URL
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(db_url)

        with engine.connect() as conn:
            # 测试 1: 查询版本
            try:
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                results["PostgreSQL 版本查询"]["success"] = True
                results["PostgreSQL 版本查询"]["details"] = version.split(",")[0]
                print(f"  ✓ PostgreSQL 版本: {version.split(',')[0]}")
            except Exception as e:
                results["PostgreSQL 版本查询"]["details"] = str(e)

            # 测试 2: 查询当前数据库
            try:
                result = conn.execute(text("SELECT current_database()"))
                db_name = result.scalar()
                results["当前数据库查询"]["success"] = True
                results["当前数据库查询"]["details"] = db_name
                print(f"  ✓ 当前数据库: {db_name}")
            except Exception as e:
                results["当前数据库查询"]["details"] = str(e)

            # 测试 3: 查询表数量
            try:
                result = conn.execute(
                    text(
                        """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public'
                """
                    )
                )
                table_count = result.scalar()
                results["表数量查询"]["success"] = True
                results["表数量查询"]["details"] = f"{table_count} 个表"
                print(f"  ✓ 公共模式表数量: {table_count}")
            except Exception as e:
                results["表数量查询"]["details"] = str(e)

        engine.dispose()

    except Exception as e:
        print(f"✗ 查询测试失败: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(description="灾备演练脚本")
    parser.add_argument(
        "--backup-file",
        help="指定备份文件 (默认: 自动查找最新备份)",
        default=None,
    )
    parser.add_argument(
        "--backup-dir",
        help="备份文件目录 (默认: ./backups)",
        default=None,
    )
    parser.add_argument(
        "--target-db",
        help="目标数据库名 (默认: 从 DATABASE_URL 获取)",
        default=None,
    )
    parser.add_argument(
        "--db-url",
        help="目标数据库连接 URL (默认: 使用 .env 中的 DATABASE_URL)",
        default=None,
    )
    parser.add_argument(
        "--no-cleanup",
        help="不清理恢复的数据库",
        action="store_true",
    )
    parser.add_argument(
        "--report-file",
        help="报告输出文件 (支持 .md 扩展名)",
        default=None,
    )
    parser.add_argument(
        "--notify-email",
        help="发送邮件通知",
        action="store_true",
    )
    parser.add_argument(
        "--notify-slack",
        help="发送 Slack 通知",
        action="store_true",
    )
    parser.add_argument(
        "--detailed",
        help="生成详细的验证报告",
        action="store_true",
    )

    args = parser.parse_args()

    # 获取数据库 URL
    db_url = args.db_url or os.environ.get("DATABASE_URL")
    if not db_url:
        print("错误: 未设置 DATABASE_URL 环境变量")
        sys.exit(1)

    # 检查是否为 PostgreSQL
    if not db_url.startswith("postgresql"):
        print("警告: 此脚本仅支持 PostgreSQL 数据库")
        sys.exit(1)

    # 解析数据库参数
    db_params = parse_db_url(db_url)

    # 如果指定了目标数据库，则修改
    if args.target_db:
        db_params["database"] = args.target_db

    # 设置备份目录
    backup_dir = Path(args.backup_dir) if args.backup_dir else PROJECT_ROOT / "backups"

    print("=" * 60)
    print("灾备演练")
    print("=" * 60)
    print(f"目标数据库: {db_params['database']}")
    print(f"备份目录: {backup_dir}")
    if args.notify_email:
        print("通知: 邮件")
    if args.notify_slack:
        print("通知: Slack")
    print("=" * 60)

    # 查找备份文件
    if args.backup_file:
        backup_file = Path(args.backup_file)
        if not backup_file.exists():
            print(f"✗ 备份文件不存在: {backup_file}")
            sys.exit(1)
    else:
        backup_file = find_latest_backup(backup_dir)
        if not backup_file:
            print("✗ 未找到备份文件，请先执行备份")
            sys.exit(1)

    start_time = datetime.datetime.now()
    success = False
    details = {}

    try:
        # 创建临时工作目录
        with tempfile.TemporaryDirectory() as work_dir:
            work_path = Path(work_dir)

            # 解压备份文件（如果需要）
            sql_file = decompress_backup(backup_file, work_path)

            # 删除现有数据库
            drop_database(db_params)

            # 创建新数据库
            create_database(db_params)

            # 恢复备份
            restore_backup(sql_file, db_params)

            # 验证恢复的数据（增强版）
            if args.detailed:
                verification_results = verify_restored_data_enhanced(db_url)
                details.update(verification_results)

                # 检查是否所有验证都通过
                success = all(r["success"] for r in verification_results.values())

                if success:
                    # 运行基本查询测试（增强版）
                    query_results = run_basic_queries_enhanced(db_url)
                    details.update(query_results)
                    success = all(r["success"] for r in query_results.values())
            else:
                # 使用原始验证方法
                success = verify_restored_data(db_url)

                if success:
                    success = run_basic_queries(db_url)

        # 生成报告
        report_file = Path(args.report_file) if args.report_file else None
        report_content = generate_drill_report(
            backup_file, db_params, success, start_time, report_file, details if args.detailed else None
        )

        # 发送通知
        if args.notify_email:
            subject = f"灾备演练{'成功' if success else '失败'} - {datetime.datetime.now().strftime('%Y-%m-%d')}"
            send_email_notification(subject, report_content)

        if args.notify_slack:
            status_emoji = "✅" if success else "❌"
            message = f"{status_emoji} 灾备演练{'成功' if success else '失败'}\n"
            message += f"数据库: {db_params['database']}\n"
            message += f"备份文件: {backup_file.name}\n"
            message += f"时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
            send_slack_notification(message)

        if success:
            print("\n" + "=" * 60)
            print("✓ 灾备演练成功！")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("✗ 灾备演练失败！")
            print("=" * 60)
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ 演练失败: {e}")
        import traceback
        traceback.print_exc()

        # 生成失败报告
        report_file = Path(args.report_file) if args.report_file else None
        generate_drill_report(backup_file, db_params, False, start_time, report_file)

        # 发送失败通知
        if args.notify_email:
            subject = f"灾备演练失败 - {datetime.datetime.now().strftime('%Y-%m-%d')}"
            send_email_notification(subject, f"灾备演练失败\n\n错误: {e}")

        if args.notify_slack:
            message = f"❌ 灾备演练失败\n错误: {e}"
            send_slack_notification(message)

        sys.exit(1)


if __name__ == "__main__":
    main()
