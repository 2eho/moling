# Test-MolingAPI.ps1
# 测试墨灵 API 完整流程

$baseUrl = "http://localhost:8001/api/v1"

Write-Host "=== 1. 注册用户 ===" -ForegroundColor Cyan
try {
    $regBody = @{
        email = "test3@moling.com"
        password = "Test@123456"
        nickname = "测试用户3"
    } | ConvertTo-Json

    $regResp = Invoke-RestMethod -Uri "$baseUrl/auth/register" -Method Post -Body $regBody -ContentType "application/json" -ErrorAction Stop
    Write-Host "✅ 注册成功: $($regResp | ConvertTo-Json)" -ForegroundColor Green
} catch {
    $errContent = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
    Write-Host "❌ 注册失败: $($errContent | ConvertTo-Json)" -ForegroundColor Red
}

Start-Sleep -Seconds 1

Write-Host "`n=== 2. 登录获取 Token ===" -ForegroundColor Cyan
$token = $null
try {
    $loginBody = @{
        email = "test3@moling.com"
        password = "Test@123456"
    } | ConvertTo-Json

    $loginResp = Invoke-RestMethod -Uri "$baseUrl/auth/login" -Method Post -Body $loginBody -ContentType "application/json" -ErrorAction Stop
    $token = $loginResp.access_token
    Write-Host "✅ 登录成功，Token 前20字符: $($token.Substring(0, [Math]::Min(20, $token.Length)))..." -ForegroundColor Green
} catch {
    $errContent = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
    Write-Host "❌ 登录失败: $($errContent | ConvertTo-Json)" -ForegroundColor Red
}

if (-not $token) {
    Write-Host "`n❌ 无法获取 Token，终止测试" -ForegroundColor Red
    exit 1
}

$headers = @{
    Authorization = "Bearer $token"
}

Start-Sleep -Seconds 1

Write-Host "`n=== 3. 获取个人信息 ===" -ForegroundColor Cyan
try {
    $meResp = Invoke-RestMethod -Uri "$baseUrl/auth/me" -Headers $headers -ErrorAction Stop
    Write-Host "✅ 获取个人信息成功: $($meResp | ConvertTo-Json)" -ForegroundColor Green
} catch {
    $errContent = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
    Write-Host "❌ 获取个人信息失败: $($errContent | ConvertTo-Json)" -ForegroundColor Red
}

Start-Sleep -Seconds 1

Write-Host "`n=== 4. 创建项目 ===" -ForegroundColor Cyan
$projectId = $null
try {
    $projBody = @{
        title = "斗破苍穹同人"
        description = "萧炎重生，再踏巅峰"
        genre = "fantasy"
    } | ConvertTo-Json

    $projResp = Invoke-RestMethod -Uri "$baseUrl/projects" -Method Post -Body $projBody -ContentType "application/json" -Headers $headers -ErrorAction Stop
    $projectId = $projResp.id
    Write-Host "✅ 创建项目成功: ID=$projectId, 标题=$($projResp.title)" -ForegroundColor Green
} catch {
    $errContent = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
    Write-Host "❌ 创建项目失败: $($errContent | ConvertTo-Json)" -ForegroundColor Red
}

Start-Sleep -Seconds 1

if ($projectId) {
    Write-Host "`n=== 5. 获取项目详情 ===" -ForegroundColor Cyan
    try {
        $projDetail = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId" -Headers $headers -ErrorAction Stop
        Write-Host "✅ 获取项目详情成功" -ForegroundColor Green
    } catch {
        $errContent = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
        Write-Host "❌ 获取项目详情失败: $($errContent | ConvertTo-Json)" -ForegroundColor Red
    }

    Write-Host "`n=== 6. 获取四库（角色） ===" -ForegroundColor Cyan
    try {
        $vaultChars = Invoke-RestMethod -Uri "$baseUrl/vault/characters?project_id=$projectId" -Headers $headers -ErrorAction Stop
        Write-Host "✅ 获取角色库成功，数量: $($vaultChars.Count)" -ForegroundColor Green
    } catch {
        $errContent = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
        Write-Host "❌ 获取角色库失败: $($errContent | ConvertTo-Json)" -ForegroundColor Red
    }
}

Write-Host "`n=== 测试完成 ===" -ForegroundColor Cyan
Write-Host "Token 状态: $(if ($token) { '✅ 有效' } else { '❌ 无效' })" -ForegroundColor $(if ($token) { 'Green' } else { 'Red' })
