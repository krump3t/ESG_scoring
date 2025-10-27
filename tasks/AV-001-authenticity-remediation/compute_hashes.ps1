# Compute real SHA256 hashes for evidence.json
$files = @(
    'C:\projects\Work Projects\.claude\full_protocol.md',
    'C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine\REMEDIATION_PLAN.md',
    'C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine\tasks\AR-001-authenticity-refactor\COMPLETION_REPORT.md',
    'C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine\artifacts\authenticity\report.json'
)

foreach ($path in $files) {
    if (Test-Path $path) {
        $hash = (Get-FileHash -Path $path -Algorithm SHA256).Hash
        Write-Host "$path | $hash"
    } else {
        Write-Host "$path | FILE_NOT_FOUND"
    }
}

# For test suite, hash first test file
$testPath = 'C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine\tests\test_authenticity_audit.py'
if (Test-Path $testPath) {
    $hash = (Get-FileHash -Path $testPath -Algorithm SHA256).Hash
    Write-Host "$testPath | $hash"
}
