<# ============================================================
 Moling Build Cleanup Script
 - Clean old Tauri/Rust build artifacts
 - Clean C drive app caches  
 - Rule: keep latest build, remove old ones; aggressive if target > 2GB

 Usage:
   powershell -File clean-builds.ps1           # normal cleanup
   powershell -File clean-builds.ps1 -DryRun   # preview only
   powershell -File clean-builds.ps1 -Aggressive # full target cleanup
 ============================================================ #>

param(
    [switch]$DryRun = $false,
    [switch]$Aggressive = $false,
    [int]$TargetSizeLimitMB = 2000
)

$ErrorActionPreference = "Stop"
$script:CleanedMB = 0
$script:ErrorList = @()

function Write-Banner($text) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Write-Info($text, $color = "White") {
    Write-Host $text -ForegroundColor $color
}

function Get-DirSizeMB($path) {
    if (-not (Test-Path $path)) { return 0 }
    try {
        $size = (Get-ChildItem $path -Recurse -File -ErrorAction Stop | Measure-Object -Property Length -Sum).Sum
        return [math]::Round($size / 1MB, 1)
    } catch {
        $script:ErrorList += "Cannot read: $path"
        return 0
    }
}

function Remove-DirSafe($path, $label) {
    if (-not (Test-Path $path)) {
        Write-Info "  [SKIP] $label - path not found" "DarkGray"
        return
    }
    $sizeMB = Get-DirSizeMB $path
    if ($sizeMB -lt 0.1) {
        Write-Info "  [SKIP] $label - already empty ($sizeMB MB)" "DarkGray"
        return
    }
    Write-Info "  [DEL] $label - $sizeMB MB" "Yellow"
    if (-not $DryRun) {
        try {
            Remove-Item $path -Recurse -Force -ErrorAction Stop
            $script:CleanedMB += $sizeMB
            Write-Info "  [OK]  Deleted $label" "Green"
        } catch {
            $script:ErrorList += "Delete failed: $path : $_"
            Write-Info "  [FAIL] $label : $_" "Red"
        }
    } else {
        $script:CleanedMB += $sizeMB
    }
}

# ============================================================
# Phase 1: Tauri Build Artifacts
# ============================================================
Write-Banner "Phase 1: Tauri/Rust Build Artifacts"

$TauriTarget = "D:\work\moling\moling-web\src-tauri\target"
$TauriTargetTotal = Get-DirSizeMB $TauriTarget
Write-Info "Tauri target total: $TauriTargetTotal MB (limit: $TargetSizeLimitMB MB)" "White"

# Rule 1.1: Full clean if target exceeds limit
if ($Aggressive -or $TauriTargetTotal -gt $TargetSizeLimitMB) {
    Write-Info "  [INFO] Target exceeds limit ($TauriTargetTotal > $TargetSizeLimitMB), full cleanup" "Magenta"
    Remove-DirSafe "$TauriTarget\debug"       "Tauri debug build artifacts"
    Remove-DirSafe "$TauriTarget\release"     "Tauri release build artifacts"
    Remove-DirSafe "$TauriTarget\.fingerprint" "Tauri fingerprint cache"
} else {
    Write-Info "  [PASS] Target size within limit" "Gray"
}

# Rule 1.2: Remove orphaned build dirs (crates no longer in Cargo.lock)
$BuildDir = "$TauriTarget\debug\build"
$LockFile = "D:\work\moling\moling-web\src-tauri\Cargo.lock"

if ((Test-Path $BuildDir) -and (Test-Path $LockFile)) {
    $CurrentCrates = Select-String -Path $LockFile -Pattern '^name = "([^"]+)"' | ForEach-Object { $_.Matches.Groups[1].Value } | Sort-Object -Unique
    Write-Info "  [INFO] $($CurrentCrates.Count) crates in Cargo.lock" "Gray"

    $DeletedBuilds = 0
    Get-ChildItem $BuildDir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $dirName = $_.Name
        $crateName = $dirName -replace '-[a-f0-9]{16}$', ''
        if ($crateName -notin $CurrentCrates) {
            $sizeMB = Get-DirSizeMB $_.FullName
            Write-Info "  [DEL] Orphaned build: $dirName - $sizeMB MB" "Yellow"
            if (-not $DryRun) {
                try {
                    Remove-Item $_.FullName -Recurse -Force -ErrorAction Stop
                    $script:CleanedMB += $sizeMB
                } catch {
                    $script:ErrorList += "Delete failed: $($_.FullName)"
                }
            } else {
                $script:CleanedMB += $sizeMB
            }
            $DeletedBuilds++
        }
    }
    Write-Info "  [INFO] Cleaned $DeletedBuilds orphaned build dirs" "$(if ($DeletedBuilds -gt 0) {'Green'} else {'Gray'})"
}

# ============================================================
# Phase 2: moling-server-rs Build Artifacts
# ============================================================
Write-Banner "Phase 2: moling-server-rs Build Artifacts"

$RsTarget = "D:\work\moling\moling-server-rs\target"
$RsTargetTotal = Get-DirSizeMB $RsTarget
Write-Info "moling-server-rs target total: $RsTargetTotal MB" "White"

if ($RsTargetTotal -gt $TargetSizeLimitMB -or $Aggressive) {
    Remove-DirSafe "$RsTarget\debug"       "moling-server-rs debug build artifacts"
    Remove-DirSafe "$RsTarget\release"     "moling-server-rs release build artifacts"
    Remove-DirSafe "$RsTarget\.fingerprint" "moling-server-rs fingerprint cache"
} else {
    Write-Info "  [PASS] Within limit" "Gray"
}

# ============================================================
# Phase 3: C Drive Tauri App Caches
# ============================================================
Write-Banner "Phase 3: C Drive Tauri App Caches"

$AppDataLocal = "$env:LOCALAPPDATA"

# Moling WebView cache (EBWebView = WebView2 browser data)
Remove-DirSafe "$AppDataLocal\com.moling.desktop\EBWebView"    "Moling WebView cache"

# AnyTrade WebView cache
Remove-DirSafe "$AppDataLocal\com.anytrade.desktop\EBWebView"  "AnyTrade WebView cache"

# Tauri WiX / NSIS tools (keep - needed for MSI/NSIS builds)
$WixSize = Get-DirSizeMB "$AppDataLocal\tauri\WixTools314"
$NsisSize = Get-DirSizeMB "$AppDataLocal\tauri\NSIS"
if ($WixSize -gt 0)  { Write-Info "  [KEEP] Tauri WiX Tools: $WixSize MB (MSI builder)" "DarkGray" }
if ($NsisSize -gt 0) { Write-Info "  [KEEP] Tauri NSIS: $NsisSize MB (installer builder)" "DarkGray" }

# ============================================================
# Phase 4: Browser / System Temp Files
# ============================================================
Write-Banner "Phase 4: Browser & System Temp"

# Edge cache
Remove-DirSafe "$AppDataLocal\Microsoft\Edge\User Data\Default\Cache"      "Edge page cache"
Remove-DirSafe "$AppDataLocal\Microsoft\Edge\User Data\Default\Code Cache" "Edge code cache"

# Windows temp (> 7 days old)
if ($Aggressive) {
    $WinTemp  = "$env:SystemRoot\Temp"
    $UserTemp = "$env:TEMP"
    Write-Info "  [INFO] Windows Temp: $(Get-DirSizeMB $WinTemp) MB" "Gray"
    Write-Info "  [INFO] User Temp: $(Get-DirSizeMB $UserTemp) MB" "Gray"

    $cutoff = (Get-Date).AddDays(-7)
    Get-ChildItem $WinTemp -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt $cutoff } | ForEach-Object {
        $script:CleanedMB += [math]::Round($_.Length / 1MB, 1)
        if (-not $DryRun) { Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue }
    }
    Get-ChildItem $UserTemp -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt $cutoff } | ForEach-Object {
        $script:CleanedMB += [math]::Round($_.Length / 1MB, 1)
        if (-not $DryRun) { Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue }
    }
    Write-Info "  [CLEAN] Removed temp files older than 7 days" "Green"
}

# ============================================================
# Summary
# ============================================================
Write-Banner "Cleanup Summary"
$ModeLabel = if ($DryRun) { "DRY RUN (preview)" } else { "EXECUTED" }
Write-Info "Mode: $ModeLabel" "White"
Write-Info "Total cleaned: $CleanedMB MB" "Green"

if ($script:ErrorList.Count -gt 0) {
    Write-Info "Errors ($($script:ErrorList.Count)):" "Red"
    $script:ErrorList | ForEach-Object { Write-Info "  $_" "Red" }
}

if (-not $DryRun) {
    $LogDir = "D:\work\moling\scripts\logs"
    if (-not (Test-Path $LogDir)) { New-Item $LogDir -ItemType Directory -Force | Out-Null }
    $LogEntry = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Cleaned ${CleanedMB}MB | Mode=$ModeLabel"
    $LogEntry | Out-File "$LogDir\clean-builds.log" -Append -Encoding UTF8
    Write-Info "Log: scripts\logs\clean-builds.log" "Gray"
}
