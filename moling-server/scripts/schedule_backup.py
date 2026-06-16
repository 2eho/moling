#!/usr/bin/env python3
"""
备份调度器（跨平台）

功能：
1. 根据配置定期执行备份
2. 支持全量和增量备份
3. 支持备份验证、加密、上传
4. 支持邮件和 Slack 通知
5. 可作为后台服务运行

使用方法：
    # 前台运行（测试用）
    python scripts/schedule_backup.py --foreground

    # 后台运行（Linux/macOS）
    python scripts/schedule_backup.py --daemon

    # 使用配置文件
    python scripts/schedule_backup.py --config /path/to/config.json

配置文件格式 (JSON)：
{
    "backup_schedule": {
        "full_backup": "0 2 * * *",      // 每天凌晨 2:00 全量备份
        "incremental_backup": "*/30 * * * *"  // 每 30 分钟增量备份
    },
    "backup_options": {
        "encrypt": true,
        "upload": "s3",
        "verify": true
    },
    "notification": {
        "email": true,
        "slack": true
    }
}

环境变量：
    DATABASE_URL: 数据库连接 URL
    BACKUP_DIR: 备份文件存储目录
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("schedule_backup")


class BackupScheduler:
    """
    备份调度器类
    """

    def __init__(self, config_file: Optional[Path] = None):
        self.config = self.load_config(config_file)
        self.script_dir = Path(__file__).parent
        self.running = False

    def load_config(self, config_file: Optional[Path]) -> dict:
        """
        加载配置文件
        """
        default_config = {
            "backup_schedule": {
                "full_backup": "0 2 * * *",  # 每天凌晨 2:00
                "incremental_backup": "*/30 * * * *",  # 每 30 分钟
            },
            "backup_options": {
                "encrypt": False,
                "upload": None,
                "verify": False,
            },
            "notification": {
                "email": False,
                "slack": False,
            },
            "backup_dir": str(PROJECT_ROOT / "backups"),
            "database_url": None,
        }

        if config_file and config_file.exists():
            logger.info(f"加载配置文件: {config_file}")
            with open(config_file, "r") as f:
                user_config = json.load(f)
                # 合并配置
                for key, value in user_config.items():
                    if key in default_config and isinstance(default_config[key], dict):
                        default_config[key].update(value)
                    else:
                        default_config[key] = value
        else:
            logger.info("使用默认配置")

        return default_config

    def parse_cron(self, cron_expr: str) -> tuple:
        """
        解析 cron 表达式（简化版）

        支持：
            * * * * * (分 时 日 月 周)
            */n (每 n 单位)
        """
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            raise ValueError(f"无效的 cron 表达式: {cron_expr}")

        minute, hour, day, month, weekday = parts

        # 简化解析（生产环境建议使用 python-cron 库）
        result = {
            "minute": self._parse_cron_part(minute, 0, 59),
            "hour": self._parse_cron_part(hour, 0, 23),
            "day": self._parse_cron_part(day, 1, 31),
            "month": self._parse_cron_part(month, 1, 12),
            "weekday": self._parse_cron_part(weekday, 0, 6),
        }

        return result

    def _parse_cron_part(self, part: str, min_val: int, max_val: int) -> list:
        """
        解析 cron 表达式的一部分
        """
        if part == "*":
            return list(range(min_val, max_val + 1))

        if part.startswith("*/"):
            step = int(part[2:])
            return list(range(min_val, max_val + 1, step))

        # 支持逗号分隔的值
        if "," in part:
            return [int(x) for x in part.split(",")]

        # 支持范围
        if "-" in part:
            start, end = part.split("-")
            return list(range(int(start), int(end) + 1))

        return [int(part)]

    def should_run(self, cron_config: dict) -> bool:
        """
        检查是否应该运行备份
        """
        now = time.localtime()

        # 检查分钟
        if now.tm_min not in cron_config["minute"]:
            return False

        # 检查小时
        if now.tm_hour not in cron_config["hour"]:
            return False

        # 检查日期
        if cron_config["day"] != [*range(1, 32)] and now.tm_mday not in cron_config["day"]:
            return False

        # 检查月份
        if cron_config["month"] != [*range(1, 13)] and now.tm_mon not in cron_config["month"]:
            return False

        # 检查星期
        if cron_config["weekday"] != [*range(0, 7)] and now.tm_wday not in cron_config["weekday"]:
            return False

        return True

    def run_backup(self, backup_type: str = "full"):
        """
        执行备份
        """
        logger.info(f"开始 {backup_type} 备份...")

        # 构建命令
        cmd = [
            sys.executable,
            str(self.script_dir / "backup_pg_dump.py"),
            "--type",
            backup_type,
            "--backup-dir",
            self.config["backup_dir"],
        ]

        # 添加选项
        options = self.config.get("backup_options", {})

        if options.get("encrypt"):
            cmd.append("--encrypt")

        if options.get("upload"):
            cmd.extend(["--upload", options["upload"]])

        if options.get("verify"):
            cmd.append("--verify")

        # 执行备份
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 小时超时
            )

            if result.returncode == 0:
                logger.info(f"✓ {backup_type} 备份成功")
                self.send_notification(f"{backup_type} 备份成功", result.stdout)
            else:
                logger.error(f"✗ {backup_type} 备份失败: {result.stderr}")
                self.send_notification(f"{backup_type} 备份失败", result.stderr)

        except subprocess.TimeoutExpired:
            logger.error(f"✗ {backup_type} 备份超时")
            self.send_notification(f"{backup_type} 备份超时", "备份执行时间超过 1 小时")

        except Exception as e:
            logger.error(f"✗ {backup_type} 备份异常: {e}")
            self.send_notification(f"{backup_type} 备份异常", str(e))

    def send_notification(self, subject: str, message: str):
        """
        发送通知
        """
        notification = self.config.get("notification", {})

        if notification.get("email"):
            logger.info("发送邮件通知...")
            # 调用 monitor_backup.py 中的邮件发送函数
            try:
                cmd = [
                    sys.executable,
                    str(self.script_dir / "monitor_backup.py"),
                    "--notify-email",
                ]
                subprocess.run(cmd, capture_output=True, timeout=60)
            except Exception as e:
                logger.error(f"邮件通知失败: {e}")

        if notification.get("slack"):
            logger.info("发送 Slack 通知...")
            try:
                cmd = [
                    sys.executable,
                    str(self.script_dir / "monitor_backup.py"),
                    "--notify-slack",
                ]
                subprocess.run(cmd, capture_output=True, timeout=60)
            except Exception as e:
                logger.error(f"Slack 通知失败: {e}")

    def run(self, foreground: bool = True):
        """
        运行调度器
        """
        self.running = True

        logger.info("备份调度器已启动")
        logger.info(f"全量备份调度: {self.config['backup_schedule']['full_backup']}")
        logger.info(f"增量备份调度: {self.config['backup_schedule']['incremental_backup']}")

        # 解析 cron 配置
        full_backup_cron = self.parse_cron(self.config["backup_schedule"]["full_backup"])
        incremental_backup_cron = self.parse_cron(self.config["backup_schedule"]["incremental_backup"])

        last_full_backup = 0
        last_incremental_backup = 0

        try:
            while self.running:
                current_time = time.time()

                # 检查是否需要运行全量备份
                if self.should_run(full_backup_cron):
                    if current_time - last_full_backup > 3600:  # 至少间隔 1 小时
                        self.run_backup("full")
                        last_full_backup = current_time

                # 检查是否需要运行增量备份
                if self.should_run(incremental_backup_cron):
                    if current_time - last_incremental_backup > 1800:  # 至少间隔 30 分钟
                        self.run_backup("incremental")
                        last_incremental_backup = current_time

                # 等待 1 分钟
                time.sleep(60)

        except KeyboardInterrupt:
            logger.info("收到停止信号，正在退出...")
            self.running = False

        except Exception as e:
            logger.error(f"调度器异常: {e}")
            raise

    def stop(self):
        """
        停止调度器
        """
        logger.info("正在停止调度器...")
        self.running = False


def main():
    parser = argparse.ArgumentParser(description="备份调度器")
    parser.add_argument(
        "--config",
        help="配置文件路径 (JSON 格式)",
        default=None,
    )
    parser.add_argument(
        "--foreground",
        help="前台运行（默认）",
        action="store_true",
        default=True,
    )
    parser.add_argument(
        "--daemon",
        help="后台运行",
        action="store_true",
    )
    parser.add_argument(
        "--test",
        help="测试模式（仅执行一次备份）",
        action="store_true",
    )

    args = parser.parse_args()

    # 加载配置
    config_file = Path(args.config) if args.config else None

    # 创建调度器
    scheduler = BackupScheduler(config_file)

    if args.test:
        # 测试模式：执行一次备份
        logger.info("测试模式：执行一次全量备份")
        scheduler.run_backup("full")
    elif args.daemon:
        # 后台运行（需要使用 systemd 或类似工具）
        logger.info("后台模式：建议使用 systemd 或 supervisor 管理")
        scheduler.run(foreground=True)
    else:
        # 前台运行
        scheduler.run(foreground=True)


if __name__ == "__main__":
    main()
