#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Fail-closed validation pipeline: tri-run -> alignment audit -> gold-lite -> NL reports

.DESCRIPTION
    Orchestrates the complete validation and export pipeline:
    1. Triple-run deterministic validation (SEED=42)
    2. Alignment audit (fail-closed: exit 2 on mismatch)
    3. Gold-lite bundle refresh
    4. NL report generation (optional)

.PARAMETER Config
    Path to companies config file (default: configs/companies_local.yaml)

.EXAMPLE
    ./scripts/validate_and_export.ps1
    ./scripts/validate_and_export.ps1 -Config configs/companies_prod.yaml
#>

param(
    [string]$Config = "configs/companies_local.yaml"
)

$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Validation & Export Pipeline - SCA v13.8-MEA" -ForegroundColor Cyan
Write-Host "Config: $Config" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Ensure environment variables are set
$env:SEED = "42"
$env:PYTHONHASHSEED = "0"
$env:WX_OFFLINE_REPLAY = "true"
$env:ALLOW_NETWORK = ""
$env:PYTHONPATH = "."
$env:RETRIEVAL_TIER = "auto"

Write-Host "`n[1/5] Triple-run deterministic validation..." -ForegroundColor Yellow

Write-Host "  Run 1/3..." -ForegroundColor Gray
.\.venv\Scripts\python.exe scripts\run_matrix.py --config $Config
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Run 1 failed" -ForegroundColor Red
    exit 1
}

Write-Host "  Run 2/3..." -ForegroundColor Gray
.\.venv\Scripts\python.exe scripts\run_matrix.py --config $Config
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Run 2 failed" -ForegroundColor Red
    exit 1
}

Write-Host "  Run 3/3..." -ForegroundColor Gray
.\.venv\Scripts\python.exe scripts\run_matrix.py --config $Config
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Run 3 failed" -ForegroundColor Red
    exit 1
}

Write-Host "  SUCCESS: Triple-run complete" -ForegroundColor Green

Write-Host "`n[2/5] Alignment audit (quote verification)..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe scripts\alignment_audit.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Alignment audit failed (quotes don't match source PDFs)" -ForegroundColor Red
    exit 2
}
Write-Host "  SUCCESS: All quotes verified" -ForegroundColor Green

Write-Host "`n[3/5] Gold-lite bundle refresh..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe scripts\refresh_gold_lite.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Gold-lite refresh failed" -ForegroundColor Red
    exit 3
}
Write-Host "  SUCCESS: Gold-lite bundle created" -ForegroundColor Green

Write-Host "`n[4/5] NL report generation..." -ForegroundColor Yellow
if (Test-Path "scripts\generate_nl_report.py") {
    .\.venv\Scripts\python.exe scripts\generate_nl_report.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: NL report generation failed" -ForegroundColor Red
        exit 4
    }
    Write-Host "  SUCCESS: NL reports generated" -ForegroundColor Green
} else {
    Write-Host "  SKIPPED: generate_nl_report.py not found" -ForegroundColor Gray
}

Write-Host "`n[5/5] Validation summary..." -ForegroundColor Yellow
if (Test-Path "artifacts\qa\SUCCESS_PIN.json") {
    $pin = Get-Content "artifacts\qa\SUCCESS_PIN.json" | ConvertFrom-Json
    Write-Host "  Timestamp: $($pin.timestamp)" -ForegroundColor Gray
    Write-Host "  Documents: $($pin.total_documents)" -ForegroundColor Gray
    Write-Host "  All identical: $($pin.all_identical)" -ForegroundColor Gray
}

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "PIPELINE COMPLETE - All validation gates passed" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan

exit 0
