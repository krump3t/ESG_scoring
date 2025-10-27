# SCA v13.8-MEA Compliance Remediation Script
# Remediates malformed task directories and validates structure
# Author: SCA Protocol v13.8
# Date: 2025-10-22

$ErrorActionPreference = "Stop"
$projectRoot = "C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SCA v13.8-MEA Compliance Remediation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Remove malformed task directories
Write-Host "[Step 1] Removing malformed task directories..." -ForegroundColor Yellow

$malformedDirs = @(
    "tasks005-microsoft-full-analysisartifacts",
    "tasks005-microsoft-full-analysiscontext",
    "tasks005-microsoft-full-analysisqa",
    "tasks005-microsoft-full-analysisreports",
    "tasks006-ghg-stage1-fixartifacts",
    "tasks006-ghg-stage1-fixcontext",
    "tasks006-ghg-stage1-fixqa",
    "tasks006-ghg-stage1-fixreports"
)

foreach ($dir in $malformedDirs) {
    $fullPath = Join-Path $projectRoot $dir
    if (Test-Path $fullPath) {
        # Check if empty
        $items = Get-ChildItem $fullPath -Force
        if ($items.Count -eq 0) {
            Remove-Item $fullPath -Force
            Write-Host "  ✓ Removed empty malformed directory: $dir" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ Malformed directory NOT empty: $dir ($($items.Count) items)" -ForegroundColor Red
            Write-Host "    Contents: $($items.Name -join ', ')" -ForegroundColor Red
            Write-Host "    Manual review required!" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Step 2: Validate proper task directory structure
Write-Host "[Step 2] Validating task directory structure..." -ForegroundColor Yellow

$tasksDir = Join-Path $projectRoot "tasks"
$taskDirs = Get-ChildItem $tasksDir -Directory | Where-Object { $_.Name -match '^\d{3}-' }

$requiredSubdirs = @("context", "artifacts", "qa", "reports")
$requiredContextFiles = @(
    "hypothesis.md",
    "design.md",
    "evidence.json",
    "data_sources.json",
    "adr.md",
    "assumptions.md",
    "cp_paths.json"
)

$complianceReport = @()

foreach ($taskDir in $taskDirs) {
    $taskName = $taskDir.Name
    $issues = @()

    # Check subdirectories
    foreach ($subdir in $requiredSubdirs) {
        $subdirPath = Join-Path $taskDir.FullName $subdir
        if (-not (Test-Path $subdirPath)) {
            $issues += "Missing subdirectory: $subdir"
        }
    }

    # Check context files
    $contextPath = Join-Path $taskDir.FullName "context"
    if (Test-Path $contextPath) {
        foreach ($file in $requiredContextFiles) {
            $filePath = Join-Path $contextPath $file
            if (-not (Test-Path $filePath)) {
                $issues += "Missing context file: $file"
            }
        }
    }

    # Check for cp_paths.json content
    $cpPathsFile = Join-Path $contextPath "cp_paths.json"
    if (Test-Path $cpPathsFile) {
        $cpContent = Get-Content $cpPathsFile -Raw | ConvertFrom-Json
        if (-not $cpContent.critical_path) {
            $issues += "cp_paths.json missing 'critical_path' field"
        }
    }

    $status = if ($issues.Count -eq 0) { "✓ COMPLIANT" } else { "✗ NON-COMPLIANT" }
    $color = if ($issues.Count -eq 0) { "Green" } else { "Red" }

    Write-Host "  $status : $taskName" -ForegroundColor $color

    if ($issues.Count -gt 0) {
        foreach ($issue in $issues) {
            Write-Host "    - $issue" -ForegroundColor Yellow
        }
    }

    $complianceReport += [PSCustomObject]@{
        Task = $taskName
        Compliant = ($issues.Count -eq 0)
        Issues = $issues
    }
}

Write-Host ""

# Step 3: Summary
Write-Host "[Step 3] Compliance Summary" -ForegroundColor Yellow

$totalTasks = $complianceReport.Count
$compliantTasks = ($complianceReport | Where-Object { $_.Compliant }).Count
$nonCompliantTasks = $totalTasks - $compliantTasks

Write-Host "  Total tasks: $totalTasks" -ForegroundColor Cyan
Write-Host "  Compliant: $compliantTasks" -ForegroundColor Green
Write-Host "  Non-compliant: $nonCompliantTasks" -ForegroundColor Red

if ($nonCompliantTasks -gt 0) {
    Write-Host ""
    Write-Host "  ⚠ REMEDIATION REQUIRED for $nonCompliantTasks tasks" -ForegroundColor Red
    Write-Host "  Next steps:" -ForegroundColor Yellow
    Write-Host "    1. Review non-compliant tasks above" -ForegroundColor Yellow
    Write-Host "    2. Create missing context artifacts" -ForegroundColor Yellow
    Write-Host "    3. Re-run this script to verify" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "  ✅ ALL TASKS COMPLIANT with SCA v13.8" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Remediation Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Export compliance report
$reportPath = Join-Path $tasksDir "COMPLIANCE_REPORT.json"
$complianceReport | ConvertTo-Json -Depth 10 | Out-File $reportPath -Encoding UTF8
Write-Host "Compliance report saved to: $reportPath" -ForegroundColor Cyan
