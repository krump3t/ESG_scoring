# === AUTHENTIC END-TO-END DEMO VALIDATION ===
# Phase 9 final validation: produce real artifacts from Headlam PDF

$ErrorActionPreference = "Stop"
$env:SEED = "42"
$env:PYTHONHASHSEED = "0"

Write-Host "=== PHASE 9: AUTHENTIC END-TO-END DEMO VALIDATION ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify source PDF
Write-Host "[1/7] Verifying source PDF..." -ForegroundColor Yellow
if (Test-Path "artifacts/raw/LSE_HEAD_2025.pdf") {
    $size = (Get-Item "artifacts/raw/LSE_HEAD_2025.pdf").Length
    Write-Host "  + PDF found: $($size / 1KB) KB" -ForegroundColor Green
} else {
    Write-Host "  X PDF not found" -ForegroundColor Red
    Write-Host "  Available files in artifacts/raw/:"
    Get-ChildItem "artifacts/raw/" -ErrorAction SilentlyContinue | Select-Object -First 10 | Format-Table Name, Length
    exit 1
}

# Step 2: Verify demo artifacts already exist from previous ingestion
Write-Host ""
Write-Host "[2/7] Checking existing demo artifacts..." -ForegroundColor Yellow
$bronze_exists = Test-Path "artifacts/demo/headlam_bronze.parquet"
$index_exists = Test-Path "artifacts/demo/index_snapshot.json"
$demo_exists = Test-Path "artifacts/demo/headlam_demo_response.json"

Write-Host "  Bronze parquet:    $(if ($bronze_exists) {'✓'} else {'✗'})" -ForegroundColor $(if ($bronze_exists) {'Green'} else {'Yellow'})
Write-Host "  Index snapshot:    $(if ($index_exists) {'✓'} else {'✗'})" -ForegroundColor $(if ($index_exists) {'Green'} else {'Yellow'})
Write-Host "  Demo response:     $(if ($demo_exists) {'✓'} else {'✗'})" -ForegroundColor $(if ($demo_exists) {'Green'} else {'Yellow'})

# Step 3: Verify index has meaningful size
Write-Host ""
Write-Host "[3/7] Verifying index snapshot quality..." -ForegroundColor Yellow
if ($index_exists) {
    $index_content = Get-Content "artifacts/demo/index_snapshot.json" -Raw | ConvertFrom-Json
    $total_docs = $index_content.total_docs
    Write-Host "  Total indexed docs: $total_docs" -ForegroundColor $(if ($total_docs -ge 5) {'Green'} else {'Red'})
    if ($total_docs -lt 5) {
        Write-Host "  ✗ Need ≥5 docs for meaningful demo" -ForegroundColor Red
        exit 2
    }
} else {
    Write-Host "  ✗ Index snapshot missing" -ForegroundColor Red
    exit 2
}

# Step 4: Produce fresh demo response via API
Write-Host ""
Write-Host "[4/7] Producing demo response via /score endpoint..." -ForegroundColor Yellow
& .venv/Scripts/python -c @"
from fastapi.testclient import TestClient
from apps.api.main import app
import json, pathlib, sys

client = TestClient(app)
payload = {
    'company': 'Headlam Group Plc',
    'year': 2025,
    'query': 'net zero by 2040; scope 3 emissions take-back trial'
}

try:
    response = client.post('/score?semantic=1&k=10&alpha=0.6', json=payload)
    resp_data = response.json()

    # Write to artifacts
    outdir = pathlib.Path('artifacts/demo')
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'headlam_demo_response.json').write_text(json.dumps(resp_data, indent=2))

    print(f'  + Response status: {response.status_code}')
    print(f'  + Scores count: {len(resp_data.get(\"scores\", []))}')
    print(f'  + Trace ID: {resp_data.get(\"trace_id\", \"\")}')

    if not resp_data.get('scores'):
        print('  X No scores in response', file=sys.stderr)
        sys.exit(3)

except Exception as e:
    print(f'  X Error: {e}', file=sys.stderr)
    sys.exit(4)
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Demo response generation failed" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Step 5: Evidence quality gate
Write-Host ""
Write-Host "[5/7] Validating evidence quality..." -ForegroundColor Yellow
& .venv/Scripts/python -c @"
import json, pathlib, sys

resp = json.loads(pathlib.Path('artifacts/demo/headlam_demo_response.json').read_text())
quotes = [
    ev.get('quote', '')
    for s in resp.get('scores', [])
    for ev in s.get('evidence', [])
]

ok = bool(quotes) and all(q.strip() and 'stub' not in q.lower() for q in quotes)
print(f'  Evidence count: {len(quotes)}')
print(f'  Quality OK: {ok}')

if not ok:
    print('  X Evidence quotes missing/low quality', file=sys.stderr)
    sys.exit(5)
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Evidence validation failed" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Step 6: Determinism verification (3× identical)
Write-Host ""
Write-Host "[6/7] Running determinism verification (3× runs)..." -ForegroundColor Yellow
& .venv/Scripts/python -c @"
from fastapi.testclient import TestClient
from apps.api.main import app
import hashlib, json, pathlib, sys

client = TestClient(app)
payload = {
    'company': 'Headlam Group Plc',
    'year': 2025,
    'query': 'net zero by 2040; scope 3 emissions take-back trial'
}

digests = []
for i in range(3):
    resp = client.post('/score?semantic=1&k=10&alpha=0.6', json=payload).json()
    core = [
        {'t': s['theme'], 'st': s['stage'], 'c': round(s['confidence'], 4)}
        for s in resp.get('scores', [])
    ]
    digest = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
    digests.append(digest)
    print(f'  Run {i+1}: {digest[:16]}...')

identical = (digests[0] == digests[1] == digests[2])
print(f'  Determinism: {\"✓ PASS\" if identical else \"✗ FAIL\"}')

# Write determinism report
pathlib.Path('artifacts/sca_qax/determinism_report.json').write_text(
    json.dumps({'runs': 3, 'digests': digests, 'identical': identical}, indent=2)
)

if not identical:
    print('  X Determinism check failed', file=sys.stderr)
    sys.exit(6)
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Determinism verification failed" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Step 7: Parity validation
Write-Host ""
Write-Host "[7/7] Verifying parity artifact..." -ForegroundColor Yellow
if (Test-Path "artifacts/pipeline_validation/demo_topk_vs_evidence.json") {
    $parity = Get-Content "artifacts/pipeline_validation/demo_topk_vs_evidence.json" -Raw | ConvertFrom-Json
    $parity_ok = $parity.parity_ok
    Write-Host "  Parity OK: $(if ($parity_ok) {'✓ true'} else {'✗ false'})" -ForegroundColor $(if ($parity_ok) {'Green'} else {'Red'})

    if (-not $parity_ok) {
        Write-Host "  ✗ Parity validation failed" -ForegroundColor Red
        exit 7
    }
} else {
    Write-Host "  ✗ Parity artifact not found" -ForegroundColor Red
    exit 7
}

# Success banner
Write-Host ""
Write-Host "=======================================================================" -ForegroundColor Green
Write-Host "AUTHENTIC DEMO VALIDATION COMPLETE" -ForegroundColor Green
Write-Host "=======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Artifacts verified:" -ForegroundColor Cyan
Write-Host "  + artifacts/demo/headlam_demo_response.json (scores + evidence)" -ForegroundColor White
Write-Host "  + artifacts/pipeline_validation/demo_topk_vs_evidence.json (parity)" -ForegroundColor White
Write-Host "  + artifacts/sca_qax/determinism_report.json (3x identical)" -ForegroundColor White
$idx_msg = "  + artifacts/demo/index_snapshot.json ({0} documents indexed)" -f $total_docs
Write-Host $idx_msg -ForegroundColor White
Write-Host ""
Write-Host "Next step: Phase 10 Bootstrap" -ForegroundColor Yellow
Write-Host "  scripts/ci/github_bootstrap.ps1" -ForegroundColor White
Write-Host ""
