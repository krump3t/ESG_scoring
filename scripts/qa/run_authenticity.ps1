# ESG Authenticity Audit Runner (PowerShell)
# Sets up environment and runs audit with determinism test

param(
    [string]$ESG_ROOT = $env:ESG_ROOT,
    [int]$Runs = 2,
    [string]$OutputDir = "artifacts/authenticity"
)

# Validate ESG_ROOT
if (-not $ESG_ROOT) {
    Write-Error "ESG_ROOT environment variable not set"
    exit 1
}

if (-not (Test-Path $ESG_ROOT)) {
    Write-Error "ESG_ROOT path does not exist: $ESG_ROOT"
    exit 1
}

# Set working directory
Set-Location $ESG_ROOT
Write-Host "Working directory: $(Get-Location)" -ForegroundColor Green

# Set environment variables for determinism
$env:PYTHONHASHSEED = "0"
$env:SEED = "42"
$env:ESG_ROOT = $ESG_ROOT
$env:GIT_COMMIT = (git rev-parse HEAD 2>$null)

Write-Host "Environment:" -ForegroundColor Green
Write-Host "  PYTHONHASHSEED: $($env:PYTHONHASHSEED)"
Write-Host "  SEED: $($env:SEED)"
Write-Host "  ESG_ROOT: $($env:ESG_ROOT)"
Write-Host "  GIT_COMMIT: $($env:GIT_COMMIT)"

# Ensure output directory exists
$OutputDirPath = Join-Path $ESG_ROOT $OutputDir
New-Item -ItemType Directory -Path $OutputDirPath -Force | Out-Null
Write-Host "Output directory: $OutputDirPath" -ForegroundColor Green

# Run tests first
Write-Host "`nRunning test suite..." -ForegroundColor Cyan
pytest -q tests/test_authenticity_audit.py -v
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Some tests failed, but continuing audit..."
}

# Run audit
Write-Host "`nRunning authenticity audit..." -ForegroundColor Cyan
python scripts/qa/authenticity_audit.py `
    --root "$ESG_ROOT" `
    --runs $Runs `
    --out "$OutputDir"

$AuditExitCode = $LASTEXITCODE

# Check outputs
Write-Host "`nAudit outputs:" -ForegroundColor Green
if (Test-Path "$OutputDirPath/report.json") {
    Write-Host "  ✓ report.json" -ForegroundColor Green
} else {
    Write-Host "  ✗ report.json (NOT FOUND)" -ForegroundColor Red
}

if (Test-Path "$OutputDirPath/report.md") {
    Write-Host "  ✓ report.md" -ForegroundColor Green
    Get-Content "$OutputDirPath/report.md" | Select-Object -First 30 | Write-Host
} else {
    Write-Host "  ✗ report.md (NOT FOUND)" -ForegroundColor Red
}

# Exit with audit status
if ($AuditExitCode -eq 0) {
    Write-Host "`nAudit PASSED" -ForegroundColor Green
} else {
    Write-Host "`nAudit FAILED" -ForegroundColor Red
}

exit $AuditExitCode
