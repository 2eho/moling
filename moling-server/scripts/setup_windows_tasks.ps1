<#
.SYNOPSIS
    墨灵项目备份任务计划配置脚本

.DESCRIPTION
    此脚本用于在 Windows 任务计划程序中创建备份任务

.NOTES
    需要以管理员身份运行
    请确保已安装 Python 和 PostgreSQL 客户端工具
#>

# 配置变量
$ProjectRoot = "C:\Users\Admin\Desktop\MolingProject"
$PythonExe = "python.exe"
$ScriptsDir = Join-Path $ProjectRoot "moling-server\scripts"
$BackupDir = Join-Path $ProjectRoot "backups"
$LogDir = Join-Path $ProjectRoot "logs"

# 确保日志目录存在
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    Write-Host "✓ 创建日志目录: $LogDir"
}

# 确保备份目录存在
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    Write-Host "✓ 创建备份目录: $BackupDir"
}

# 任务配置
$Tasks = @(
    @{
        Name = "Moling-Full-Backup"
        Description = "墨灵项目全量备份（每天凌晨 2:00）"
        Script = Join-Path $ScriptsDir "backup_pg_dump.py"
        Arguments = "--type full --backup-dir `"$BackupDir`" --encrypt"
        Schedule = "Daily"
        At = "02:00"
        LogFile = Join-Path $LogDir "backup.log"
    },
    @{
        Name = "Moling-Incremental-Backup"
        Description = "墨灵项目增量备份（每 30 分钟）"
        Script = Join-Path $ScriptsDir "backup_pg_dump.py"
        Arguments = "--type incremental --backup-dir `"$BackupDir`""
        Schedule = "Minutes"
        Interval = 30
        LogFile = Join-Path $LogDir "backup_incremental.log"
    },
    @{
        Name = "Moling-Backup-Monitor"
        Description = "墨灵项目备份监控（每天凌晨 3:00）"
        Script = Join-Path $ScriptsDir "monitor_backup.py"
        Arguments = "--notify-email --notify-slack"
        Schedule = "Daily"
        At = "03:00"
        LogFile = Join-Path $LogDir "monitor.log"
    },
    @{
        Name = "Moling-Disaster-Recovery-Drill"
        Description = "墨灵项目灾备演练（每周日凌晨 4:00）"
        Script = Join-Path $ScriptsDir "disaster_recovery_drill.py"
        Arguments = "--notify-email --notify-slack --report-file `"$LogDir\drill_report_$(Get-Date -Format 'yyyyMMdd').md`""
        Schedule = "Weekly"
        DaysOfWeek = @("Sunday")
        At = "04:00"
        LogFile = Join-Path $LogDir "drill.log"
    }
)

# 创建任务
foreach ($TaskConfig in $Tasks) {
    $TaskName = $TaskConfig.Name
    $ScriptPath = $TaskConfig.Script
    $LogFile = $TaskConfig.LogFile

    Write-Host "`n正在配置任务: $TaskName"

    # 检查任务是否已存在
    $ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

    if ($ExistingTask) {
        Write-Host "  任务已存在，正在删除..."
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    # 创建动作
    $Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "$ScriptPath $($TaskConfig.Arguments) >> `"$LogFile`" 2>&1"

    # 创建触发器
    switch ($TaskConfig.Schedule) {
        "Daily" {
            $Trigger = New-ScheduledTaskTrigger -Daily -At $TaskConfig.At
        }
        "Weekly" {
            $Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $TaskConfig.DaysOfWeek -At $TaskConfig.At
        }
        "Minutes" {
            $Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $TaskConfig.Interval)
        }
    }

    # 创建设置
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

    # 创建主体（使用当前用户）
    $Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

    # 注册任务
    Register-ScheduledTask -TaskName $TaskName -Description $TaskConfig.Description -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal

    Write-Host "  ✓ 任务已创建: $TaskName"
}

Write-Host "`n`n所有备份任务已配置完成！"
Write-Host "`n任务列表："
Get-ScheduledTask -TaskName "Moling-*" | Format-Table -Property TaskName, State, Description

Write-Host "`n注意事项："
Write-Host "1. 请确保已配置环境变量（DATABASE_URL, GPG_RECIPIENT 等）"
Write-Host "2. 请确保 PostgreSQL 客户端工具已安装（pg_dump, psql 等）"
Write-Host "3. 请确保 Python 已安装且可在 PATH 中访问"
Write-Host "4. 测试任务：右键点击任务 -> 运行"
Write-Host "5. 查看日志：在 $LogDir 目录中"
