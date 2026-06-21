#!/usr/bin/env python3
"""
备份监控脚本

功能：
1. 检查最新备份的时间
2. 如果备份超过指定时间（默认 24 小时），发送告警
3. 检查备份文件大小（如果太小，可能备份失败）
4. 支持邮件和 Slack 通知

使用方法：
    # 基本使用
    python scripts/monitor_backup.py

    # 指定备份目录
    python scripts/monitor_backup.py --backup-dir /path/to/backups

    # 修改告警阈值（小时）
    python scripts/monitor_backup.py --max-age-hours 48

    # 发送通知
    python scripts/monitor_backup.py --notify-email --notify-slack

环境变量：
    BACKUP_DIR: 备份文件目录 (默认: ./backups)
    MAX_BACKUP_AGE_HOURS: 最大备份年龄（小时）(默认: 24)
    MIN_BACKUP_SIZE_MB: 最小备份大小（MB）(默认: 1)
    SMTP_SERVER, SMTP_USER, SMTP_PASSWORD: 邮件通知配置
    SLACK_WEBHOOK_URL: Slack 通知配置
"""

from __future__ import annotations

import argparse
import datetime
import os
import smtplib
import sys
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


def find_latest_backup(backup_dir: Path, backup_type: str = "full") -> Path | None:
    """
    查找最新的备份文件

    参数：
        backup_dir: 备份目录
        backup_type: 备份类型 (full/incremental)

    返回：
        最新的备份文件路径，如果没有找到则返回 None
    """
    # 查找匹配的备份文件
    pattern = f"*_{backup_type}_*.sql*"
    backups = list(backup_dir.glob(pattern))

    if not backups:
        return None

    # 按修改时间排序，获取最新的
    latest = max(backups, key=lambda p: p.stat().st_mtime)
    return latest


def check_backup_age(backup_file: Path, max_age_hours: int) -> tuple[bool, float]:
    """
    检查备份文件年龄

    返回：
        (是否过期, 年龄（小时）)
    """
    file_mtime = datetime.datetime.fromtimestamp(backup_file.stat().st_mtime)
    age = datetime.datetime.now() - file_mtime
    age_hours = age.total_seconds() / 3600

    is_expired = age_hours > max_age_hours

    return is_expired, age_hours


def check_backup_size(backup_file: Path, min_size_mb: float) -> tuple[bool, float]:
    """
    检查备份文件大小

    返回：
        (是否正常, 大小（MB）)
    """
    size_mb = backup_file.stat().st_size / (1024 * 1024)
    is_normal = size_mb >= min_size_mb

    return is_normal, size_mb


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
    """
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
        return False

    if not recipients:
        print("✗ 错误: 未指定收件人")
        return False

    print(f"\n发送邮件通知到: {', '.join(recipients)}")

    try:
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))

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
    """
    if not HAS_REQUESTS:
        print("✗ 错误: 未安装 requests")
        return False

    webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")

    if not webhook_url:
        print("✗ 错误: 未设置 SLACK_WEBHOOK_URL")
        return False

    print("\n发送 Slack 通知...")

    try:
        payload = {
            "text": message,
            "username": "备份监控机器人",
            "icon_emoji": ":warning:",
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
            print(f"✗ Slack 通知发送失败: {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Slack 通知发送失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="备份监控脚本")
    parser.add_argument(
        "--backup-dir",
        help="备份文件目录 (默认: ./backups)",
        default=None,
    )
    parser.add_argument(
        "--backup-type",
        choices=["full", "incremental"],
        default="full",
        help="备份类型 (默认: full)",
    )
    parser.add_argument(
        "--max-age-hours",
        type=float,
        help="最大备份年龄（小时）(默认: 24)",
        default=None,
    )
    parser.add_argument(
        "--min-size-mb",
        type=float,
        help="最小备份大小（MB）(默认: 1)",
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
        "--quiet",
        help="安静模式（仅在有问题时输出）",
        action="store_true",
    )

    args = parser.parse_args()

    # 获取配置
    backup_dir = (
        Path(args.backup_dir) if args.backup_dir else Path(os.environ.get("BACKUP_DIR", PROJECT_ROOT / "backups"))
    )
    max_age_hours = (
        args.max_age_hours if args.max_age_hours is not None else float(os.environ.get("MAX_BACKUP_AGE_HOURS", "24"))
    )
    min_size_mb = args.min_size_mb if args.min_size_mb is not None else float(os.environ.get("MIN_BACKUP_SIZE_MB", "1"))

    if not args.quiet:
        print("=" * 60)
        print("备份监控")
        print("=" * 60)
        print(f"备份目录: {backup_dir}")
        print(f"最大年龄: {max_age_hours} 小时")
        print(f"最小大小: {min_size_mb} MB")
        print("=" * 60)

    # 检查备份目录
    if not backup_dir.exists():
        error_msg = f"✗ 备份目录不存在: {backup_dir}"
        print(error_msg)

        if args.notify_email or args.notify_slack:
            subject = "备份监控告警 - 备份目录不存在"
            body = f"{error_msg}\n\n请检查备份配置。"
            send_email_notification(subject, body, [])
            send_slack_notification(f"🚨 {subject}\n{body}")

        sys.exit(1)

    # 查找最新备份
    latest_backup = find_latest_backup(backup_dir, args.backup_type)

    if not latest_backup:
        error_msg = f"✗ 未找到 {args.backup_type} 类型的备份文件"
        print(error_msg)

        if args.notify_email or args.notify_slack:
            subject = "备份监控告警 - 未找到备份文件"
            body = f"{error_msg}\n\n请检查备份任务是否正常运行。"
            send_email_notification(subject, body, [])
            send_slack_notification(f"🚨 {subject}\n{body}")

        sys.exit(1)

    if not args.quiet:
        print(f"\n最新备份: {latest_backup.name}")
        print(f"  路径: {latest_backup}")

    # 检查备份年龄
    is_expired, age_hours = check_backup_age(latest_backup, max_age_hours)

    if is_expired:
        warning_msg = f"⚠ 备份已过期: {age_hours:.1f} 小时 (最大: {max_age_hours} 小时)"
        print(warning_msg)

        if args.notify_email or args.notify_slack:
            subject = "备份监控告警 - 备份已过期"
            body = f"{warning_msg}\n\n"
            body += f"备份文件: {latest_backup.name}\n"
            mtime = latest_backup.stat().st_mtime
            body += f"备份时间: {datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
            body += f"当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            body += "\n请检查备份任务是否正常运行。"

            send_email_notification(subject, body, [])
            send_slack_notification(f"🚨 {subject}\n{warning_msg}")

        sys.exit(1)
    else:
        if not args.quiet:
            print(f"  年龄: {age_hours:.1f} 小时 ✓")

    # 检查备份大小
    is_normal, size_mb = check_backup_size(latest_backup, min_size_mb)

    if not is_normal:
        warning_msg = f"⚠ 备份文件过小: {size_mb:.2f} MB (最小: {min_size_mb} MB)"
        print(warning_msg)

        if args.notify_email or args.notify_slack:
            subject = "备份监控告警 - 备份文件过小"
            body = f"{warning_msg}\n\n"
            body += f"备份文件: {latest_backup.name}\n"
            body += f"文件大小: {size_mb:.2f} MB\n"
            body += "\n备份可能失败，请检查备份日志。"

            send_email_notification(subject, body, [])
            send_slack_notification(f"🚨 {subject}\n{warning_msg}")

        sys.exit(1)
    else:
        if not args.quiet:
            print(f"  大小: {size_mb:.2f} MB ✓")

    # 一切正常
    if not args.quiet:
        print("\n" + "=" * 60)
        print("✓ 备份监控正常")
        print("=" * 60)

    sys.exit(0)


if __name__ == "__main__":
    main()
