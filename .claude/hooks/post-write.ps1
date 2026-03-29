# post-write.ps1
# PostToolUse (Write) 훅 — 파일 저장 시 pytest 자동 실행
# 트리거: Claude가 .py 파일을 저장할 때마다 자동 실행

param(
    [string]$ToolName = "",
    [string]$FilePath = ""
)

# Python 파일이 아니면 스킵
if ($FilePath -and $FilePath -notmatch "\.py$") {
    exit 0
}

# 테스트 파일 자체가 저장된 경우 → 해당 테스트만 실행
# 구현 파일이 저장된 경우 → 대응하는 테스트 파일 실행 시도
$testFile = ""

if ($FilePath -match "test_.*\.py$") {
    $testFile = $FilePath
} elseif ($FilePath -match "\.py$") {
    # 대응하는 테스트 파일 탐색
    $dir = Split-Path $FilePath -Parent
    $fileName = Split-Path $FilePath -Leaf
    $baseName = $fileName -replace "\.py$", ""
    $candidate = Join-Path (Split-Path $dir -Parent) "tests" "test_$baseName.py"
    if (Test-Path $candidate) {
        $testFile = $candidate
    }
}

# pytest 실행
$pytestArgs = if ($testFile -and (Test-Path $testFile)) {
    @($testFile, "-v", "--tb=short", "-x")
} else {
    @("--tb=short", "-x", "-q")
}

Write-Host ""
Write-Host "🧪 [Hook] pytest 자동 실행..." -ForegroundColor Cyan

$result = & python -m pytest @pytestArgs 2>&1
$exitCode = $LASTEXITCODE

Write-Host $result

if ($exitCode -eq 0) {
    Write-Host "✅ 테스트 통과 (Green)" -ForegroundColor Green
} else {
    Write-Host "❌ 테스트 실패 (Red) — 구현 코드를 수정하세요." -ForegroundColor Red
}

exit $exitCode
