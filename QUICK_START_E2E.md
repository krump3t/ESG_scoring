# QUICK START: E2E Demo Execution
## Post-Remediation Quick Reference

**Status**: ✅ All blockers resolved - Ready to run
**Working Directory**: `C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine`

---

## OPTION 1: Quick Validation Test (5 minutes)

Test that all fixes work before running full E2E demo.

### PowerShell Commands

```powershell
cd "C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"

# 1. Verify imports
python -c "from agents.extraction.enhanced_pdf_extractor import extract_pdf_chunks; print('OK: extract_pdf_chunks')"
python -c "from agents.crawler.provider_local import discover_from_config; print('OK: provider_local')"
python -c "import json; print(f'OK: companies.json - {len(json.load(open(\"artifacts/demo/companies.json\")))} companies')"

# 2. Test single PDF ingestion (Apple)
$env:SEED="42"
$env:PYTHONHASHSEED="0"

python scripts/ingest_single_doc.py `
  --org-id AAPL `
  --year 2023 `
  --pdf-path "data/pdf_cache/Apple_2023_sustainability.pdf" `
  --source-url "file://data/pdf_cache/Apple_2023_sustainability.pdf"

# 3. Verify output
dir data\silver\org_id=AAPL\year=2023\

# Expected files:
#   AAPL_2023_chunks.jsonl
#   AAPL_2023_chunks.parquet
#   ingestion_manifest.json
```

**If all 3 steps pass**: ✅ System is ready for full E2E demo

---

## OPTION 2: Full E2E Demo (Cold Start)

Run the complete end-to-end pipeline with determinism validation.

### Prerequisites

```powershell
cd "C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"

# Ensure virtual environment activated
.\.venv\Scripts\Activate.ps1

# Verify dependencies (should already be installed)
python -c "import fitz, duckdb, yaml; print('Dependencies OK')"
```

### Step 1: Ingestion (Local PDFs → Silver Parquet)

```powershell
# Set deterministic environment
$env:SEED="42"
$env:PYTHONHASHSEED="0"

# Ingest all local PDFs from companies_local.yaml
python scripts/ingest_local_matrix.py --config configs/companies_local.yaml

# Expected output:
# {"status":"ok","ingested":3}  # AAPL, XOM, JPM (MSFT already processed)
```

### Step 2: Parquet Validation (DuckDB Queries)

```powershell
# Quick sanity check using DuckDB
python -c @"
import duckdb
con = duckdb.connect()
df = con.execute('''
  SELECT doc_id, COUNT(*) chunks, MIN(page) min_page, MAX(page) max_page,
         SUM(LENGTH(text)>=30) ge30, SUM(LENGTH(text)=0 OR text IS NULL) empty
  FROM read_parquet('data/silver/org_id=*/year=*/*_chunks.parquet')
  GROUP BY doc_id ORDER BY chunks DESC;
''').fetchdf()
print(df)
"@
```

### Step 3: Offline Replay (3× Determinism Test)

```powershell
# Ensure offline mode (no network calls)
Remove-Item Env:ALLOW_NETWORK -ErrorAction SilentlyContinue
$env:WX_OFFLINE_REPLAY="true"

# Create output directory
Remove-Item -Force -Recurse artifacts\matrix_determinism -ErrorAction SilentlyContinue
mkdir artifacts\matrix_determinism

# Run 3× identical scoring
python scripts/run_matrix.py --config configs/companies_local.yaml | Out-File artifacts\matrix_determinism\run1.txt -Encoding utf8
python scripts/run_matrix.py --config configs/companies_local.yaml | Out-File artifacts\matrix_determinism\run2.txt -Encoding utf8
python scripts/run_matrix.py --config configs/companies_local.yaml | Out-File artifacts\matrix_determinism\run3.txt -Encoding utf8
```

### Step 4: Determinism Validation

```powershell
# Compute and compare hashes
python -c @"
import hashlib, json
from pathlib import Path

p = Path('artifacts/matrix_determinism')
h1 = hashlib.sha256((p/'run1.txt').read_bytes()).hexdigest()
h2 = hashlib.sha256((p/'run2.txt').read_bytes()).hexdigest()
h3 = hashlib.sha256((p/'run3.txt').read_bytes()).hexdigest()

print(f'Run 1: {h1[:16]}...')
print(f'Run 2: {h2[:16]}...')
print(f'Run 3: {h3[:16]}...')
print(f'\nDeterminism: {\"PASS\" if h1==h2==h3 else \"FAIL\"}')

# Save report
rep = {'hashes': [h1, h2, h3], 'identical': h1==h2==h3}
(p/'determinism_report.json').write_text(json.dumps(rep, indent=2))
"@
```

### Step 5: Validate Gates (Parity, Evidence, RD)

```powershell
# Check gate validation artifacts
dir artifacts\matrix\msft_2023\pipeline_validation\

# Expected files:
#   demo_topk_vs_evidence.json  (parity check)
#   evidence_audit.json         (evidence per theme)
#   rd_sources.json             (RD theme sources)

# Inspect parity
python -c "import json; print(json.dumps(json.load(open('artifacts/matrix/msft_2023/pipeline_validation/demo_topk_vs_evidence.json')), indent=2))"

# Inspect evidence
python -c "import json; print(json.dumps(json.load(open('artifacts/matrix/msft_2023/pipeline_validation/evidence_audit.json')), indent=2))"
```

### Step 6: Review Output Contracts

```powershell
# Per-document contract
python -c "import json; print(json.dumps(json.load(open('artifacts/matrix/msft_2023/output_contract.json')), indent=2))"

# Matrix-level contract
python -c "import json; print(json.dumps(json.load(open('artifacts/matrix/matrix_contract.json')), indent=2))"
```

---

## OPTION 3: Bash Script (Git Bash / WSL)

If using Bash instead of PowerShell:

```bash
cd "/c/projects/Work Projects/ibm-projects/ESG Evaluation/prospecting-engine"

# Set environment
export SEED=42 PYTHONHASHSEED=0 WX_OFFLINE_REPLAY=true

# Run ingestion
python scripts/ingest_local_matrix.py --config configs/companies_local.yaml

# Run 3× replay
mkdir -p artifacts/matrix_determinism
python scripts/run_matrix.py --config configs/companies_local.yaml > artifacts/matrix_determinism/run1.txt
python scripts/run_matrix.py --config configs/companies_local.yaml > artifacts/matrix_determinism/run2.txt
python scripts/run_matrix.py --config configs/companies_local.yaml > artifacts/matrix_determinism/run3.txt

# Validate determinism
python -c "
import hashlib, json
from pathlib import Path
p = Path('artifacts/matrix_determinism')
h = [hashlib.sha256((p/f'run{i}.txt').read_bytes()).hexdigest() for i in (1,2,3)]
print(f'Determinism: {\"PASS\" if len(set(h))==1 else \"FAIL\"}')
(p/'determinism_report.json').write_text(json.dumps({'hashes':h,'identical':len(set(h))==1},indent=2))
"
```

---

## EXPECTED OUTPUTS

### After Ingestion

```
data/silver/
├── org_id=AAPL/
│   └── year=2023/
│       ├── AAPL_2023_chunks.jsonl
│       ├── AAPL_2023_chunks.parquet
│       └── ingestion_manifest.json
├── org_id=XOM/
│   └── year=2023/
│       ├── XOM_2023_chunks.jsonl
│       ├── XOM_2023_chunks.parquet
│       └── ingestion_manifest.json
└── org_id=JPM/
    └── year=2023/
        ├── JPM_2023_chunks.jsonl
        ├── JPM_2023_chunks.parquet
        └── ingestion_manifest.json
```

### After Matrix Replay

```
artifacts/matrix/
├── msft_2023/
│   ├── baseline/
│   │   ├── run_1/
│   │   │   ├── output.json
│   │   │   ├── scoring_response.json
│   │   │   └── hash.txt
│   │   ├── run_2/
│   │   ├── run_3/
│   │   └── determinism_report.json
│   ├── pipeline_validation/
│   │   ├── demo_topk_vs_evidence.json
│   │   ├── evidence_audit.json
│   │   └── rd_sources.json
│   └── output_contract.json
├── apple_2023/
│   └── ...
└── matrix_contract.json
```

### Gate Status (Success)

**determinism_report.json**:
```json
{
  "hashes": ["abc123...", "abc123...", "abc123..."],
  "identical": true
}
```

**output_contract.json**:
```json
{
  "doc_id": "msft_2023",
  "status": "ok",
  "gates": {
    "determinism": "PASS",
    "parity": "PASS",
    "evidence": "PASS",
    "authenticity": "PASS"
  }
}
```

---

## TROUBLESHOOTING

### Issue: Import Error for `extract_pdf_chunks`

```
ModuleNotFoundError: No module named 'agents.extraction'
```

**Fix**:
```powershell
# Add repo root to PYTHONPATH
$env:PYTHONPATH="C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"
```

### Issue: PDF Not Found

```
FileNotFoundError: data/pdf_cache/Apple_2023_sustainability.pdf
```

**Fix**: Verify PDF paths in `configs/companies_local.yaml` match actual files:
```powershell
dir data\pdf_cache\*.pdf
```

### Issue: Determinism Hash Mismatch

```
Run 1: abc123...
Run 2: def456...  # Different!
Determinism: FAIL
```

**Causes**:
1. `SEED` or `PYTHONHASHSEED` not set
2. Non-deterministic timestamp in output
3. Dictionary ordering issues

**Fix**:
```powershell
# Ensure environment variables set BEFORE running
$env:SEED="42"
$env:PYTHONHASHSEED="0"

# Restart Python interpreter
python scripts/run_matrix.py ...
```

### Issue: companies.json Not Found

```
FileNotFoundError: No companies manifest found
```

**Fix**: Verify file exists and has correct content:
```powershell
type artifacts\demo\companies.json
```

If missing, re-run:
```powershell
# (Command from BLOCKERS_RESOLVED.md to recreate file)
```

---

## SUCCESS CRITERIA

✅ **System Ready** if ALL of these pass:

1. **Import Tests**:
   - `extract_pdf_chunks` imports successfully
   - `provider_local` imports successfully
   - `companies.json` loads as valid JSON

2. **Ingestion**:
   - 3 PDFs ingested (AAPL, XOM, JPM)
   - Parquet files created with >0 chunks
   - DuckDB queries return data

3. **Determinism**:
   - 3 runs produce identical hashes
   - `determinism_report.json` shows `"identical": true`

4. **Gates**:
   - Parity: `"parity_ok": true`
   - Evidence: All themes have ≥2 pages
   - Output contracts: `"status": "ok"`

---

## NEXT STEPS AFTER SUCCESS

1. **Generate NL Reports** (if script available):
   ```powershell
   python scripts/generate_nl_report.py --config configs/companies_local.yaml
   ```

2. **Create Release Pack**:
   ```powershell
   # Bundle all artifacts, gates, and attestation manifest
   # (See original bash script section #13)
   ```

3. **Run With Live Embeddings** (optional):
   ```powershell
   # Set IBM Cloud credentials
   $env:WX_API_KEY="your-ibm-api-key"
   $env:WX_PROJECT="your-project-id"
   $env:ALLOW_NETWORK="true"

   # Run semantic fetch
   python scripts/semantic_fetch_replay.py --phase fetch --doc-id msft_2023
   ```

---

**End of Quick Start Guide**
