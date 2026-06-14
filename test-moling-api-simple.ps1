# Test-MolingAPI-simple.ps1
# 简单测试墨灵 API

$base = "http://localhost:8001/api/v1"

Write-Host "=== 1. 注册 ===" -ForegroundColor Cyan
$reg = @{ email = "test4@moling.com"; password = "Test@123456"; nickname = "测试4" } | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "$base/auth/register" -Method Post -Body $reg -ContentType "application/json"
    Write-Host "✅ 注册成功: $($r | ConvertTo-Json)" -ForegroundColor Green
} catch {
    $msg = $_.ErrorDetails.Message
    Write-Host "❌ 注册失败: $msg" -ForegroundColor Red
}

Start-Sleep -Seconds 1

Write-Host "`n=== 2. 登录 ===" -ForegroundColor Cyan
$token = $null
$login = @{ email = "test4@moling.com"; password = "Test@123456" } | ConvertTo-Json
try {
    $r = Invoke-RestMethod -Uri "$base/auth/login" -Method Post -Body $login -ContentType "application/json"
    $token = $r.access_token
    Write-Host "✅ 登录成功，Token 前20字符: $($token.Substring(0, [Math]::Min(20, $token.Length)))..." -ForegroundColor Green
} catch {
    $msg = $_.ErrorDetails.Message
    Write-Host "❌ 登录失败: $msg" -ForegroundColor Red
}

if (-not $token) {
    Write-Host "`n❌ 无法获取 Token，终止测试" -ForegroundColor Red
    exit 1
}

$hdrs = @{ Authorization = "Bearer $token" }

Start-Sleep -Seconds 1

Write-Host "`n=== 3. 获取个人信息 ===" -ForegroundColor Cyan
try {
    $r = Invoke-RestMethod -Uri "$base/auth/me" -Headers $hdrs
    Write-Host "✅ 获取成功: $($r | ConvertTo-Json)" -ForegroundColor Green
} catch {
    $msg = $_.ErrorDetails.Message
    Write-Host "❌ 获取失败: $msg" -ForegroundColor Red
}

Start-Sleep -Seconds 1

Write-Host "`n=== 4. 创建项目 ===" -ForegroundColor Cyan
$proj = @{ title = "斗破苍穹同人"; description = "萧炎重生，再踏巅峰"; genre = "fantasy" } | ConvertTo-Json
$projId = $null
try {
    $r = Invoke-RestMethod -Uri "$base/projects" -Method Post -Body $proj -ContentType "application/json" -Headers $hdrs
    $projId = $r.id
    Write-Host "✅ 创建成功: ID=$projId, 标题=$($r.title)" -ForegroundColor Green
} catch {
    $msg = $_.ErrorDetails.Message
    Write-Host "❌ 创建失败: $msg" -ForegroundColor Red
}

Start-Sleep -Seconds 1

if ($projId) {
    Write-Host "`n=== 5. 获取项目详情 ===" -ForegroundColor Cyan
    try {
        $r = Invoke-RestMethod -Uri "$base/projects/$projId" -Headers $hdrs
        Write-Host "✅ 获取成功: $($r | ConvertTo-Json)" -ForegroundColor Green
    } catch {
        $msg = $_.ErrorDetails.Message
        Write-Host "❌ 获取失败: $msg" -ForegroundColor Red
    }

    Write-Host "`n=== 6. 获取四库（角色） ===" -ForegroundColor Cyan
    try {
        $r = Invoke-RestMethod -Uri "$base/vault/characters?project_id=$projId" -Headers $hdrs
        Write-Host "✅ 获取成功，数量: $($r.Count)" -ForegroundColor Green
    } catch {
        $msg = $_.ErrorDetails.Message
        Write-Host "❌ 获取失败: $msg" -ForegroundColor Red
    }
}

Write-Host "`n=== 测试完成 ===" -ForegroundColor Cyan
