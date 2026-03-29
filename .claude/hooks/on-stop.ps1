# on-stop.ps1
# Stop 훅 — Claude 응답 완료 후 ruff 자동 실행
# 트리거: Claude가 응답을 마칠 때마다 자동 실행 (백그라운드)

# ruff가 설치되어 있는지 확인
$ruffExists = Get-Command ruff -ErrorAction SilentlyContinue
if (-not $ruffExists) {
    # ruff 없으면 조용히 종료
    exit 0
}

# 변경된 Python 파일이 있는지 확인
$changedFiles = git diff --name-only 2>$null | Where-Object { $_ -match "\.py$" }
$stagedFiles  = git diff --cached --name-only 2>$null | Where-Object { $_ -match "\.py$" }
$allChanged   = ($changedFiles + $stagedFiles) | Select-Object -Unique

if (-not $allChanged) {
    exit 0
}

Write-Host ""
Write-Host "🔍 [Hook] ruff 자동 체크..." -ForegroundColor Cyan

# 린트 체크 (수정 없이 — 문제만 보고)
$lintResult = & ruff check . 2>&1
$lintExit = $LASTEXITCODE

# 포맷 체크 (수정 없이 — 차이만 보고)
$fmtResult = & ruff format --check . 2>&1
$fmtExit = $LASTEXITCODE

if ($lintExit -eq 0 -and $fmtExit -eq 0) {
    Write-Host "✅ 린트/포맷 이상 없음" -ForegroundColor Green
} else {
    if ($lintExit -ne 0) {
        Write-Host "⚠️  린트 경고:" -ForegroundColor Yellow
        Write-Host $lintResult
    }
    if ($fmtExit -ne 0) {
        Write-Host "⚠️  포맷 불일치 (ruff format . 로 수정 가능)" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "👉 /commit 실행 시 자동 수정됩니다." -ForegroundColor DarkGray
}

# 알림음 + 토스트 (기존 Stop 훅 기능 유지)
Add-Type -AssemblyName System.Windows.Forms
[System.Media.SystemSounds]::Asterisk.Play()
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $true
$n.ShowBalloonTip(3000, "Claude Code", "응답 완료 - 입력 대기 중", [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Milliseconds 3500
$n.Dispose()

exit 0
