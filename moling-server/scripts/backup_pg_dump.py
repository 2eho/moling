#!/usr/bin/env python3
"""
数据库备份脚本 (使用 pg_dump)

功能：
1. 全量备份 (Full Backup)
2. 增量备份 (Incremental Backup) - 使用 pgBackRest 或 WAL-E
3. 备份压缩、加密 (GPG)
4. 备份上传到云存储 (S3, GCS, Azure)
5. 备份验证 (恢复到临时数据库)

使用方法：
    # 全量备份
    python scripts/backup_pg_dump.py --type full

    # 增量备份 (需要配置 pgBackRest)
    python scripts/backup_pg_dump.py --type incremental

    # 启用加密
    python scripts/backup_pg_dump.py --type full --encrypt

    # 上传到 S3
    python scripts/backup_pg_dump.py --type full --upload s3

    # 验证备份
    python scripts/backup_pg_dump.py --type full --verify

环境变量：
    DATABASE_URL: 数据库连接 URL
    BACKUP_DIR: 备份文件存储目录 (默认: ./backups)
    RETENTION_DAYS: 备份保留天数 (默认: 30)
    GPG_RECIPIENT: GPG 加密接收者 (默认: 无加密)
    S3_BUCKET: S3 存储桶名称
    S3_PREFIX: S3 对象前缀 (默认: backups/)
    AZURE_CONTAINER: Azure Blob 容器名称
    GCS_BUCKET: Google Cloud Storage 存储桶名称
"""

from __future__ import annotations

import argparse
import datetime
import gzip
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 可选依赖检查
try:
    import boto3

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

try:
    from azure.storage.blob import BlobServiceClient

    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False

try:
    from google.cloud import storage as gcs

    HAS_GCS = True
except ImportError:
    HAS_GCS = False


def parse_db_url(db_url: str) -> dict:
    """
    解析数据库连接 URL

    返回：
        dict: 包含 host, port, user, password, database 的字典
    """
    # 简单的 URL 解析（生产环境建议使用 urllib.parse）
    # 格式: postgresql://user:password@host:port/database
    # Strip scheme prefix, including any +driver suffix (e.g. +psycopg, +asyncpg)
    url = re.sub(r'^postgresql(?:\+[^:/]+)?://', '', db_url)

    # 提取用户名和密码
    if "@" in url:
        user_pass, rest = url.split("@", 1)
        if ":" in user_pass:
            user, password = user_pass.split(":", 1)
        else:
            user, password = user_pass, ""
    else:
        user, password, rest = "postgres", "", url

    # 提取主机、端口和数据库
    if "/" in rest:
        host_port, database = rest.split("/", 1)
    else:
        host_port, database = rest, "postgres"

    # 提取主机和端口
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


def create_backup_dir(backup_dir: Path) -> Path:
    """创建备份目录"""
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def get_backup_filename(backup_type: str, database: str) -> str:
    """生成备份文件名"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{database}_{backup_type}_{timestamp}.sql"


def backup_full(db_url: str, backup_dir: Path, compress: bool = True) -> Path:
    """
    执行全量备份

    使用 pg_dump 创建完整数据库备份
    """
    db_params = parse_db_url(db_url)
    backup_file = backup_dir / get_backup_filename("full", db_params["database"])

    print(f"开始全量备份: {backup_file.name}")

    # 构建 pg_dump 命令
    env = os.environ.copy()
    if db_params["password"]:
        env["PGPASSWORD"] = db_params["password"]

    cmd = [
        "pg_dump",
        f"--host={db_params['host']}",
        f"--port={db_params['port']}",
        f"--username={db_params['user']}",
        f"--dbname={db_params['database']}",
        "--no-password",
        "--verbose",
        "--clean",
        "--create",
        "--format=plain",
    ]

    try:
        # 执行 pg_dump
        with open(backup_file, "w") as f:
            subprocess.run(
                cmd,
                env=env,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )

        print(f"✓ 备份完成: {backup_file}")

        # 压缩备份文件
        if compress:
            print("压缩备份文件...")
            compressed_file = backup_file.with_suffix(".sql.gz")
            with open(backup_file, "rb") as f_in:
                with gzip.open(compressed_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            backup_file.unlink()  # 删除未压缩的文件
            backup_file = compressed_file
            print(f"✓ 压缩完成: {backup_file}")

        # 获取文件大小
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        print(f"备份大小: {size_mb:.2f} MB")

        return backup_file

    except subprocess.CalledProcessError as e:
        print(f"✗ 备份失败: {e.stderr}")
        raise
    except FileNotFoundError:
        print("✗ 错误: 未找到 pg_dump 命令")
        print("请确保 PostgreSQL 客户端工具已安装并添加到 PATH")
        raise


def backup_incremental(db_url: str, backup_dir: Path) -> Path:
    """
    执行增量备份

    注意：真正的增量备份需要 WAL 归档
    这里实现的是使用 pg_dump 的 --schema-only 和 --data-only 选项
    或者使用自定义格式并在恢复时使用增量恢复
    """
    print("注意: 真正的增量备份需要配置 WAL 归档")
    print("建议使用 pgBackRest 或 WAL-G 进行增量备份")
    print("这里提供的是基于 pg_dump 的差异化备份（不完整）")

    # 这里只是示例，生产环境应使用专业工具
    db_params = parse_db_url(db_url)
    backup_file = backup_dir / get_backup_filename("incremental", db_params["database"])

    print(f"开始增量备份: {backup_file.name}")
    print("提示: 请考虑使用 pgBackRest 获得真正的增量备份功能")

    # 临时返回一个占位符
    return backup_file


def cleanup_old_backups(backup_dir: Path, retention_days: int):
    """
    清理旧备份文件

    删除超过保留天数的备份文件
    """
    print(f"\n清理 {retention_days} 天前的备份文件...")

    cutoff = datetime.datetime.now() - datetime.timedelta(days=retention_days)
    deleted_count = 0

    for backup_file in backup_dir.glob("*.sql*"):
        if backup_file.stat().st_mtime < cutoff.timestamp():
            print(f"  删除: {backup_file.name}")
            backup_file.unlink()
            deleted_count += 1

    print(f"✓ 清理完成，删除了 {deleted_count} 个文件")


def encrypt_backup(backup_file: Path, recipient: str = None) -> Path:
    """
    使用 GPG 加密备份文件

    参数：
        backup_file: 要加密的备份文件
        recipient: GPG 接收者 (使用环境变量 GPG_RECIPIENT 如果未指定)

    返回：
        加密后的文件路径 (.gpg 后缀)
    """
    recipient = recipient or os.environ.get("GPG_RECIPIENT")

    if not recipient:
        print("警告: 未设置 GPG_RECIPIENT，跳过加密")
        return backup_file

    print("\n使用 GPG 加密备份文件...")

    encrypted_file = backup_file.with_suffix(backup_file.suffix + ".gpg")

    try:
        cmd = [
            "gpg",
            "--encrypt",
            "--recipient",
            recipient,
            "--output",
            str(encrypted_file),
            str(backup_file),
        ]

        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        print(f"✓ 加密完成: {encrypted_file.name}")

        # 删除原始文件
        backup_file.unlink()
        print(f"  原始文件已删除: {backup_file.name}")

        return encrypted_file

    except subprocess.CalledProcessError as e:
        print(f"✗ GPG 加密失败: {e.stderr}")
        raise
    except FileNotFoundError:
        print("✗ 错误: 未找到 gpg 命令")
        print("请确保 GPG 已安装并添加到 PATH")
        raise


def decrypt_backup(encrypted_file: Path, output_file: Path = None) -> Path:
    """
    解密 GPG 加密的备份文件

    参数：
        encrypted_file: 加密的备份文件 (.gpg)
        output_file: 解密后的输出文件 (默认: 移除 .gpg 后缀)

    返回：
        解密后的文件路径
    """
    if output_file is None:
        output_file = encrypted_file.with_suffix("")

    print(f"\n解密备份文件: {encrypted_file.name}")

    try:
        cmd = [
            "gpg",
            "--decrypt",
            "--output",
            str(output_file),
            str(encrypted_file),
        ]

        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        print(f"✓ 解密完成: {output_file.name}")
        return output_file

    except subprocess.CalledProcessError as e:
        print(f"✗ GPG 解密失败: {e.stderr}")
        raise


def upload_to_s3(backup_file: Path, bucket: str, prefix: str = "backups/"):
    """
    上传备份文件到 AWS S3

    需要环境变量：
        AWS_ACCESS_KEY_ID
        AWS_SECRET_ACCESS_KEY
        AWS_DEFAULT_REGION (可选)
    """
    if not HAS_BOTO3:
        print("✗ 错误: 未安装 boto3")
        print("请运行: pip install boto3")
        raise ImportError("boto3 is required for S3 upload")

    print(f"\n上传备份到 S3: s3://{bucket}/{prefix}{backup_file.name}")

    try:
        s3_client = boto3.client("s3")

        s3_client.upload_file(
            str(backup_file),
            bucket,
            f"{prefix}{backup_file.name}",
        )

        print(f"✓ 上传完成: s3://{bucket}/{prefix}{backup_file.name}")

    except Exception as e:
        print(f"✗ S3 上传失败: {e}")
        raise


def upload_to_azure(backup_file: Path, container: str):
    """
    上传备份文件到 Azure Blob Storage

    需要环境变量：
        AZURE_STORAGE_CONNECTION_STRING
        或 AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY
    """
    if not HAS_AZURE:
        print("✗ 错误: 未安装 azure-storage-blob")
        print("请运行: pip install azure-storage-blob")
        raise ImportError("azure-storage-blob is required for Azure upload")

    print(f"\n上传备份到 Azure: {container}/{backup_file.name}")

    try:
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        if connection_string:
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        else:
            account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
            account_key = os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
            if not account_name or not account_key:
                raise ValueError("未设置 Azure 存储凭证")
            blob_service_client = BlobServiceClient(
                account_url=f"https://{account_name}.blob.core.windows.net",
                credential=account_key,
            )

        blob_client = blob_service_client.get_blob_client(container=container, blob=backup_file.name)

        with open(backup_file, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

        print(f"✓ 上传完成: {container}/{backup_file.name}")

    except Exception as e:
        print(f"✗ Azure 上传失败: {e}")
        raise


def upload_to_gcs(backup_file: Path, bucket: str, prefix: str = "backups/"):
    """
    上传备份文件到 Google Cloud Storage

    需要环境变量：
        GOOGLE_APPLICATION_CREDENTIALS (指向服务账号密钥文件)
    """
    if not HAS_GCS:
        print("✗ 错误: 未安装 google-cloud-storage")
        print("请运行: pip install google-cloud-storage")
        raise ImportError("google-cloud-storage is required for GCS upload")

    print(f"\n上传备份到 GCS: gs://{bucket}/{prefix}{backup_file.name}")

    try:
        client = gcs.Client()
        bucket_obj = client.bucket(bucket)
        blob = bucket_obj.blob(f"{prefix}{backup_file.name}")

        blob.upload_from_filename(str(backup_file))

        print(f"✓ 上传完成: gs://{bucket}/{prefix}{backup_file.name}")

    except Exception as e:
        print(f"✗ GCS 上传失败: {e}")
        raise


def verify_backup(backup_file: Path) -> bool:
    """
    验证备份文件完整性

    检查：
    1. 文件存在
    2. 文件大小 > 0
    3. 对于 .gz 文件，尝试解压验证
    4. 对于 .gpg 文件，尝试解密验证
    """
    print(f"\n验证备份文件: {backup_file.name}")

    if not backup_file.exists():
        print("✗ 备份文件不存在")
        return False

    if backup_file.stat().st_size == 0:
        print("✗ 备份文件为空")
        return False

    # 验证 GPG 文件
    if backup_file.suffix == ".gpg":
        print("  提示: GPG 加密文件，跳过内容验证（需要解密密钥）")
        print("✓ 备份文件验证通过 (仅检查文件存在性和大小)")
        return True

    # 验证 gzip 文件
    if backup_file.suffix == ".gz":
        try:
            with gzip.open(backup_file, "rb") as f:
                f.read(1024)  # 尝试读取前 1KB
            print("✓ Gzip 文件验证通过")
        except Exception as e:
            print(f"✗ Gzip 文件验证失败: {e}")
            return False

    print("✓ 备份文件验证通过")
    return True


def verify_backup_by_restore(backup_file: Path, db_url: str) -> bool:
    """
    通过恢复备份到临时数据库来验证备份

    步骤：
    1. 创建临时数据库
    2. 恢复备份到临时数据库
    3. 运行测试查询
    4. 删除临时数据库

    返回：
        bool: 验证是否成功
    """
    print(f"\n通过恢复验证备份: {backup_file.name}")

    # 解析数据库参数
    db_params = parse_db_url(db_url)

    # 创建临时数据库名称
    temp_db = f"{db_params['database']}_verify_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    temp_db_params = db_params.copy()
    temp_db_params["database"] = temp_db

    print(f"  临时数据库: {temp_db}")

    # 处理加密文件
    work_dir = tempfile.mkdtemp()
    work_path = Path(work_dir)
    restore_file = backup_file

    try:
        # 如果是 GPG 文件，先解密
        if backup_file.suffix == ".gpg":
            decrypted = decrypt_backup(backup_file, work_path / backup_file.stem)
            restore_file = decrypted

        # 如果是 .gz 文件，解压
        if restore_file.suffix == ".gz":
            print("  解压备份文件...")
            decompressed = work_path / restore_file.stem
            with gzip.open(restore_file, "rb") as f_in:
                with open(decompressed, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            restore_file = decompressed

        # 创建临时数据库
        env = os.environ.copy()
        if temp_db_params["password"]:
            env["PGPASSWORD"] = temp_db_params["password"]

        create_cmd = [
            "createdb",
            f"--host={temp_db_params['host']}",
            f"--port={temp_db_params['port']}",
            f"--username={temp_db_params['user']}",
            "--no-password",
            temp_db,
        ]

        subprocess.run(create_cmd, env=env, capture_output=True, check=True)
        print("  ✓ 临时数据库已创建")

        # 恢复备份
        restore_cmd = [
            "psql",
            f"--host={temp_db_params['host']}",
            f"--port={temp_db_params['port']}",
            f"--username={temp_db_params['user']}",
            f"--dbname={temp_db}",
            "--no-password",
            "--file",
            str(restore_file),
        ]

        subprocess.run(restore_cmd, env=env, capture_output=True, text=True, check=True)
        print("  ✓ 备份已恢复到临时数据库")

        # 运行测试查询
        test_cmd = [
            "psql",
            f"--host={temp_db_params['host']}",
            f"--port={temp_db_params['port']}",
            f"--username={temp_db_params['user']}",
            f"--dbname={temp_db}",
            "--no-password",
            "--command",
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';",
        ]

        result = subprocess.run(test_cmd, env=env, capture_output=True, text=True, check=True)
        table_count = result.stdout.strip()
        print(f"  ✓ 测试查询成功: {table_count} 个表")

        print("✓ 备份验证成功（通过恢复）")
        return True

    except subprocess.CalledProcessError as e:
        print(f"✗ 备份验证失败: {e.stderr if e.stderr else e.stdout}")
        return False

    except Exception as e:
        print(f"✗ 备份验证失败: {e}")
        return False

    finally:
        # 清理：删除临时数据库
        try:
            drop_cmd = [
                "dropdb",
                f"--host={temp_db_params['host']}",
                f"--port={temp_db_params['port']}",
                f"--username={temp_db_params['user']}",
                "--no-password",
                "--if-exists",
                temp_db,
            ]
            subprocess.run(drop_cmd, env=env, capture_output=True, check=False)
            print(f"  临时数据库已清理: {temp_db}")
        except Exception:
            pass

        # 清理临时文件
        try:
            shutil.rmtree(work_dir)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="数据库备份脚本 (pg_dump)")
    parser.add_argument(
        "--type",
        choices=["full", "incremental"],
        default="full",
        help="备份类型 (默认: full)",
    )
    parser.add_argument(
        "--backup-dir",
        help="备份文件存储目录 (默认: ./backups)",
        default=None,
    )
    parser.add_argument(
        "--db-url",
        help="数据库连接 URL (默认: 使用 .env 中的 DATABASE_URL)",
        default=None,
    )
    parser.add_argument(
        "--no-compress",
        help="不压缩备份文件",
        action="store_true",
    )
    parser.add_argument(
        "--encrypt",
        help="使用 GPG 加密备份文件",
        action="store_true",
    )
    parser.add_argument(
        "--gpg-recipient",
        help="GPG 接收者 (默认: 使用 GPG_RECIPIENT 环境变量)",
        default=None,
    )
    parser.add_argument(
        "--upload",
        choices=["s3", "azure", "gcs"],
        help="上传备份到云存储",
        default=None,
    )
    parser.add_argument(
        "--verify",
        help="验证备份（恢复到临时数据库）",
        action="store_true",
    )
    parser.add_argument(
        "--no-cleanup",
        help="不清理旧备份",
        action="store_true",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        help="备份保留天数 (默认: 30)",
        default=30,
    )

    args = parser.parse_args()

    # 获取数据库 URL
    db_url = args.db_url or os.environ.get("DATABASE_URL")
    if not db_url:
        print("错误: 未设置 DATABASE_URL 环境变量")
        print("请设置 DATABASE_URL 或使用 --db-url 参数")
        sys.exit(1)

    # 检查是否为 PostgreSQL
    if not db_url.startswith("postgresql"):
        print("警告: 此脚本仅支持 PostgreSQL 数据库")
        print(f"当前数据库: {db_url.split('://')[0]}")
        print("建议使用 SQLite 备份方法（如 sqlite3 backup 命令）")
        sys.exit(1)

    # 设置备份目录
    backup_dir = Path(args.backup_dir) if args.backup_dir else PROJECT_ROOT / "backups"
    create_backup_dir(backup_dir)

    print("=" * 60)
    print("数据库备份")
    print("=" * 60)
    print(f"数据库: {parse_db_url(db_url)['database']}")
    print(f"备份目录: {backup_dir}")
    print(f"备份类型: {args.type}")
    if args.encrypt:
        print("加密: 启用 (GPG)")
    if args.upload:
        print(f"上传: {args.upload}")
    if args.verify:
        print("验证: 启用（恢复验证）")
    print("=" * 60)

    try:
        # 执行备份
        if args.type == "full":
            backup_file = backup_full(db_url, backup_dir, compress=not args.no_compress)
        else:
            backup_file = backup_incremental(db_url, backup_dir)
            if backup_file:  # 如果增量备份返回了文件
                pass
            else:
                print("✗ 增量备份未完成")
                sys.exit(1)

        # 验证备份（基本验证）
        if not verify_backup(backup_file):
            print("✗ 备份验证失败")
            sys.exit(1)

        # 加密备份
        if args.encrypt:
            backup_file = encrypt_backup(backup_file, args.gpg_recipient)

        # 上传到云存储
        if args.upload == "s3":
            bucket = os.environ.get("S3_BUCKET")
            if not bucket:
                print("✗ 错误: 未设置 S3_BUCKET 环境变量")
                sys.exit(1)
            prefix = os.environ.get("S3_PREFIX", "backups/")
            upload_to_s3(backup_file, bucket, prefix)

        elif args.upload == "azure":
            container = os.environ.get("AZURE_CONTAINER")
            if not container:
                print("✗ 错误: 未设置 AZURE_CONTAINER 环境变量")
                sys.exit(1)
            upload_to_azure(backup_file, container)

        elif args.upload == "gcs":
            bucket = os.environ.get("GCS_BUCKET")
            if not bucket:
                print("✗ 错误: 未设置 GCS_BUCKET 环境变量")
                sys.exit(1)
            prefix = os.environ.get("GCS_PREFIX", "backups/")
            upload_to_gcs(backup_file, bucket, prefix)

        # 验证备份（恢复验证）
        if args.verify:
            if not verify_backup_by_restore(backup_file, db_url):
                print("✗ 备份恢复验证失败")
                sys.exit(1)

        # 清理旧备份
        if not args.no_cleanup:
            cleanup_old_backups(backup_dir, args.retention_days)

        print("\n" + "=" * 60)
        print("✓ 备份完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 备份失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
