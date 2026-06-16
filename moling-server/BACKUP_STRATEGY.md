# 墨灵项目备份与灾备策略文档

**版本**: 1.0.0  
**最后更新**: 2026-06-16  
**维护者**: 墨灵项目团队

---

## 目录

1. [概述](#概述)
2. [备份策略](#备份策略)
3. [备份脚本使用指南](#备份脚本使用指南)
4. [自动化调度配置](#自动化调度配置)
5. [备份验证](#备份验证)
6. [灾备演练](#灾备演练)
7. [监控与告警](#监控与告警)
8. [环境配置](#环境配置)
9. [恢复流程](#恢复流程)
10. [故障排查](#故障排查)
11. [附录](#附录)

---

## 概述

本文档描述了墨灵项目的数据库备份、灾备演练和监控策略。我们的目标是：

- **RPO (Recovery Point Objective)**: 30 分钟（增量备份频率）
- **RTO (Recovery Time Objective)**: 4 小时（从备份恢复到正常运行）
- **备份保留期**: 30 天（可根据合规要求调整）
- **演练频率**: 每周一次

---

## 备份策略

### 备份类型

| 备份类型 | 频率 | 保留期 | 用途 |
|---------|------|--------|------|
| 全量备份 | 每天凌晨 2:00 | 30 天 | 完整恢复点 |
| 增量备份 | 每 30 分钟 | 7 天 | 减少 RPO |
| WAL 归档 | 实时 | 7 天 | 时间点恢复 (PITR) |

### 备份存储

1. **本地存储**: 备份文件存储在本地磁盘（默认: `./backups/`）
2. **云存储**: 可选上传到 S3 / Azure Blob / Google Cloud Storage
3. **离线存储**:  important 备份应定期归档到离线存储

### 备份加密

- 使用 GPG 加密备份文件
- 加密密钥应安全保管（建议使用密钥管理系统）
- 未加密的备份文件应在加密后删除

---

## 备份脚本使用指南

### 1. 全量备份

```bash
# 基本使用
python scripts/backup_pg_dump.py --type full

# 指定数据库连接
python scripts/backup_pg_dump.py --type full --db-url "postgresql://user:pass@host:5432/dbname"

# 指定备份目录
python scripts/backup_pg_dump.py --type full --backup-dir /path/to/backups

# 不压缩（默认启用压缩）
python scripts/backup_pg_dump.py --type full --no-compress

# 不清理旧备份
python scripts/backup_pg_dump.py --type full --no-cleanup
```

### 2. 加密备份

```bash
# 启用 GPG 加密
python scripts/backup_pg_dump.py --type full --encrypt

# 指定 GPG 接收者
python scripts/backup_pg_dump.py --type full --encrypt --gpg-recipient "backup@example.com"
```

**注意**: 需要先配置 GPG 密钥（参见 [环境配置 - GPG 配置](#gpg-配置)）

### 3. 上传到云存储

```bash
# 上传到 AWS S3
python scripts/backup_pg_dump.py --type full --upload s3

# 上传到 Azure Blob Storage
python scripts/backup_pg_dump.py --type full --upload azure

# 上传到 Google Cloud Storage
python scripts/backup_pg_dump.py --type full --upload gcs
```

**注意**: 需要先配置云存储凭证（参见 [环境配置 - 云存储配置](#云存储配置)）

### 4. 备份验证

```bash
# 基本验证（检查文件存在性、大小、压缩完整性）
python scripts/backup_pg_dump.py --type full

# 增强验证（恢复到临时数据库并运行测试查询）
python scripts/backup_pg_dump.py --type full --verify
```

---

## 自动化调度配置

### Linux (cron)

1. **安装 cron 配置**:

```bash
# 复制 cron 配置文件
sudo cp moling-server/scripts/cron.d/moling-backup /etc/cron.d/

# 设置权限
sudo chmod 644 /etc/cron.d/moling-backup

# 重启 cron 服务
sudo systemctl restart cron  # 或 sudo service cron restart
```

2. **查看调度任务**:

```bash
sudo crontab -l
```

3. **手动执行备份测试**:

```bash
sudo -u postgres python /opt/moling/moling-server/scripts/backup_pg_dump.py --type full
```

### Windows (任务计划程序)

1. **以管理员身份运行 PowerShell**:
2. **执行配置脚本**:

```powershell
.\moling-server\scripts\setup_windows_tasks.ps1
```

3. **验证任务已创建**:

```powershell
Get-ScheduledTask -TaskName "Moling-*"
```

4. **手动运行任务**:

```powershell
Start-ScheduledTask -TaskName "Moling-Full-Backup"
```

### Docker (docker-compose)

在 `docker-compose.yml` 中添加 cron 服务：

```yaml
version: '3.8'

services:
  # ... 其他服务 ...

  backup:
    image: postgres:15
    container_name: moling-backup
    volumes:
      - ./moling-server/scripts:/scripts
      - ./backups:/backups
      - ./logs:/logs
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/moling
      - GPG_RECIPIENT=backup@example.com
      - S3_BUCKET=my-moling-backups
    command: >
      bash -c "
        apt-get update && apt-get install -y cron gpg python3 python3-pip &&
        pip3 install boto3 python-dotenv &&
        crontab /scripts/cron.d/moling-backup &&
        service cron start &&
        tail -f /var/log/cron.log
      "
    depends_on:
      - db
    restart: unless-stopped
```

---

## 备份验证

### 自动验证

备份脚本会自动执行以下验证：

1. **文件存在性**: 检查备份文件是否已创建
2. **文件大小**: 检查备份文件是否大于 0
3. **压缩完整性**: 对于 `.gz` 文件，尝试解压前 1KB
4. **恢复验证** (可选): 恢复到临时数据库并运行测试查询

### 手动验证

```bash
# 检查最新备份
ls -lh backups/ | tail -5

# 验证备份文件完整性
gzip -t backups/moling_full_20260616_020000.sql.gz

# 测试恢复（到临时数据库）
python scripts/disaster_recovery_drill.py --backup-file backups/moling_full_20260616_020000.sql.gz
```

---

## 灾备演练

### 自动化演练

```bash
# 基本演练（使用最新备份）
python scripts/disaster_recovery_drill.py

# 指定备份文件
python scripts/disaster_recovery_drill.py --backup-file /path/to/backup.sql.gz

# 指定目标数据库
python scripts/disaster_recovery_drill.py --target-db moling_test_restored

# 生成详细报告
python scripts/disaster_recovery_drill.py --detailed --report-file drill_report.md

# 发送通知
python scripts/disaster_recovery_drill.py --notify-email --notify-slack
```

### 演练步骤

1. **准备阶段**:
   - 确保备份文件存在且完整
   - 确保目标数据库可访问
   - 通知相关人员

2. **执行阶段**:
   - 创建临时数据库
   - 恢复备份到临时数据库
   - 验证数据完整性
   - 运行测试查询

3. **验证阶段**:
   - 检查所有表是否已恢复
   - 检查数据行数是否正确
   - 运行应用程序测试（可选）

4. **清理阶段**:
   - 删除临时数据库
   - 生成演练报告
   - 发送通知

### 演练报告示例

演练报告会保存到 Markdown 文件，包含：

- 演练时间、耗时
- 备份文件信息
- 目标数据库信息
- 验证详情（每个测试步骤的结果）
- 建议

---

## 监控与告警

### 备份监控脚本

```bash
# 基本使用
python scripts/monitor_backup.py

# 指定阈值
python scripts/monitor_backup.py --max-age-hours 48 --min-size-mb 10

# 发送通知
python scripts/monitor_backup.py --notify-email --notify-slack

# 安静模式（仅在有问题时输出）
python scripts/monitor_backup.py --quiet
```

### 告警规则

| 指标 | 阈值 | 级别 | 动作 |
|------|------|------|------|
| 备份年龄 | > 24 小时 | 警告 | 发送邮件/Slack 通知 |
| 备份年龄 | > 48 小时 | 严重 | 立即通知 + 创建 incident |
| 备份大小 | < 1 MB | 警告 | 检查备份日志 |
| 备份文件缺失 | - | 严重 | 立即通知 |

### 集成到监控系统中

#### Prometheus + Grafana

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'moling-backup'
    static_configs:
      - targets: ['localhost:9090']

    # 使用 node_exporter textfile collector
    # 在 cron 中添加：
    # python scripts/monitor_backup.py --export-prometheus /var/lib/node_exporter/backup.prom
```

#### Nagios / Icinga

```bash
# 在 NRPE 配置中添加
command[check_moling_backup]=/usr/lib/nagios/plugins/check_moling_backup.sh
```

---

## 环境配置

### 环境变量

创建 `.env` 文件（或修改系统环境变量）：

```bash
# 数据库配置
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/moling

# 备份配置
BACKUP_DIR=/var/backups/moling
RETENTION_DAYS=30
MAX_BACKUP_AGE_HOURS=24
MIN_BACKUP_SIZE_MB=1

# GPG 配置
GPG_RECIPIENT=backup@example.com

# AWS S3 配置
S3_BUCKET=my-moling-backups
S3_PREFIX=backups/
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# Azure Blob Storage 配置
AZURE_CONTAINER=backups
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
# 或
AZURE_STORAGE_ACCOUNT_NAME=your_account_name
AZURE_STORAGE_ACCOUNT_KEY=your_account_key

# Google Cloud Storage 配置
GCS_BUCKET=my-moling-backups
GCS_PREFIX=backups/
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# 邮件通知配置
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
NOTIFICATION_EMAIL_FROM=noreply@example.com
NOTIFICATION_EMAIL_TO=admin@example.com,ops@example.com

# Slack 通知配置
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
```

### GPG 配置

#### 生成 GPG 密钥对

```bash
# 生成密钥对（交互式）
gpg --full-generate-key

# 或使用批处理模式
cat > gpg-key.params <<EOF
%echo Generating GPG key
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: Moling Backup
Name-Email: backup@moling.com
Expire-Date: 0
%pubring pubring.gpg
%secring secring.gpg
%commit
%echo done
EOF

gpg --batch --gen-key gpg-key.params
```

#### 导出公钥（用于加密）

```bash
# 导出公钥
gpg --export --armor backup@moling.com > backup_pubkey.asc

# 在其他服务器上导入公钥
gpg --import backup_pubkey.asc
```

#### 备份私钥（重要！）

```bash
# 导出私钥（妥善保管！）
gpg --export-secret-keys --armor backup@moling.com > backup_private_key.asc

# 将私钥存储到安全位置（如密钥管理系统）
```

### 云存储配置

#### AWS S3

1. 创建 S3 存储桶:
   ```bash
   aws s3 mb s3://my-moling-backups
   ```

2. 设置生命周期规则（自动删除旧备份）:
   ```bash
   aws s3api put-bucket-lifecycle-configuration --bucket my-moling-backups --lifecycle-configuration file://lifecycle.json
   ```

   `lifecycle.json`:
   ```json
   {
     "Rules": [
       {
         "ID": "Delete old backups",
         "Status": "Enabled",
         "Prefix": "backups/",
         "ExpirationInDays": 30
       }
     ]
   }
   ```

#### Azure Blob Storage

1. 创建存储账户和容器:
   ```bash
   az storage account create --name molingbackups --resource-group my-resource-group --location eastus
   az storage container create --name backups --account-name molingbackups
   ```

#### Google Cloud Storage

1. 创建存储桶:
   ```bash
   gsutil mb gs://my-moling-backups
   ```

2. 设置生命周期策略:
   ```bash
   gsutil lifecycle set lifecycle.json gs://my-moling-backups
   ```

---

## 恢复流程

### 从全量备份恢复

```bash
# 1. 解密备份（如果加密了）
gpg --decrypt backups/moling_full_20260616_020000.sql.gz.gpg > backup.sql.gz

# 2. 解压缩
gunzip backup.sql.gz

# 3. 删除现有数据库（慎重！）
dropdb -h localhost -U postgres moling

# 4. 创建新数据库
createdb -h localhost -U postgres moling

# 5. 恢复备份
psql -h localhost -U postgres -d moling -f backup.sql

# 或使用 Python 脚本
python scripts/disaster_recovery_drill.py --backup-file backups/moling_full_20260616_020000.sql.gz --target-db moling_restored
```

### 时间点恢复 (PITR)

**注意**: 需要使用 WAL 归档（配置 `archive_mode = on` 和 `archive_command`）

```bash
# 1. 恢复全量备份到临时目录
rm -rf /var/lib/postgresql/15/restore
cp -r /var/backups/moling/base_backup /var/lib/postgresql/15/restore

# 2. 创建 recovery.signal 文件
touch /var/lib/postgresql/15/restore/recovery.signal

# 3. 配置 postgresql.conf
cat >> /var/lib/postgresql/15/restore/postgresql.conf <<EOF
restore_command = 'cp /var/backups/moling/wal/%f %p'
recovery_target_time = '2026-06-15 10:00:00'
EOF

# 4. 启动 PostgreSQL
pg_ctl -D /var/lib/postgresql/15/restore start

# 5. 验证恢复
psql -h localhost -U postgres -d moling -c "SELECT NOW();"

# 6. 结束恢复（使数据库可写）
psql -h localhost -U postgres -c "SELECT pg_wal_replay_resume();"
```

---

## 故障排查

### 常见问题

#### 1. 备份失败：`pg_dump: command not found`

**解决方案**:
```bash
# 安装 PostgreSQL 客户端工具
# Ubuntu/Debian:
sudo apt-get install -y postgresql-client

# CentOS/RHEL:
sudo yum install -y postgresql

# macOS:
brew install postgresql
```

#### 2. 备份失败：`connection to database failed`

**解决方案**:
- 检查 `DATABASE_URL` 是否正确
- 检查数据库是否正在运行: `pg_isready -h localhost -p 5432`
- 检查防火墙规则
- 检查数据库用户权限

#### 3. GPG 加密失败：`gpg: encryption failed: No public key`

**解决方案**:
- 确保已导入公钥: `gpg --list-keys`
- 确保 `GPG_RECIPIENT` 正确
- 导入公钥: `gpg --import pubkey.asc`

#### 4. 云存储上传失败：`NoCredentialsError`

**解决方案**:
- 确保已配置凭证环境变量
- AWS: 运行 `aws configure`
- Azure: 检查连接字符串
- GCS: 确保服务账号密钥文件存在

#### 5. 灾备演练失败：`database already exists`

**解决方案**:
```bash
# 手动删除数据库
dropdb -h localhost -U postgres moling_test_restored

# 或指定不同的目标数据库
python scripts/disaster_recovery_drill.py --target-db moling_test_restored_v2
```

### 日志文件

- 备份日志: `logs/backup.log`
- 增量备份日志: `logs/backup_incremental.log`
- 监控日志: `logs/monitor.log`
- 演练日志: `logs/drill.log`

### 获取帮助

```bash
# 备份脚本帮助
python scripts/backup_pg_dump.py --help

# 灾备演练脚本帮助
python scripts/disaster_recovery_drill.py --help

# 监控脚本帮助
python scripts/monitor_backup.py --help
```

---

## 附录

### A. 生产环境建议

1. **使用 pgBackRest**:
   - 对于生产环境，建议使用 `pgBackRest` 替代 `pg_dump`
   - pgBackRest 支持真正的增量备份、压缩、加密和并行恢复
   - 安装: `sudo apt-get install pgbackrest`

2. **WAL 归档**:
   - 配置 WAL 归档以实现时间点恢复 (PITR)
   - 修改 `postgresql.conf`:
     ```ini
     archive_mode = on
     archive_command = 'cp %p /var/backups/moling/wal/%f'
     wal_level = replica
     ```

3. **备份服务器**:
   - 使用单独的备份服务器，避免影响生产性能
   - 备份服务器应位于不同的可用区/区域

4. **定期测试**:
   - 每周至少进行一次完整的灾备演练
   - 记录 RTO 和 RPO，持续优化

### B. 合规要求

根据行业标准和法规要求：

- **GDPR**: 备份数据应包含个人信息，需加密存储
- **HIPAA**: 医疗数据备份需加密且访问受限
- **PCI-DSS**: 支付数据备份需加密，保留期符合要求
- **SOX**: 财务数据备份需保留 7 年

### C. 性能指标

| 指标 | 目标值 | 监控频率 |
|------|--------|----------|
| 备份成功率 | 99.9% | 实时 |
| 备份执行时间 | < 1 小时 | 每次备份 |
| 备份大小 | 稳定（异常增长告警） | 每次备份 |
| 恢复验证成功率 | 100% | 每次演练 |
| RTO | < 4 小时 | 每次演练 |
| RPO | < 30 分钟 | 持续 |

### D. 联系人

- **备份负责人**: backup-team@moling.com
- **DBA 团队**: dba@moling.com
- **SRE 团队**: sre@moling.com
- **紧急联系**: oncall@moling.com

---

**文档版本历史**:

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| 1.0.0 | 2026-06-16 | 墨灵项目团队 | 初始版本 |

---

**注意事项**:

1. 本文档应定期更新（至少每季度一次）
2. 所有备份和演练记录应保留至少 1 年
3. 恢复流程应至少每季度测试一次
4. 密钥和凭证应定期轮换（建议每 90 天）

---

**END OF DOCUMENT**
