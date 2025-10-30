# Live Multi-Source ESG Ingestion - Quick Start

## What This Is

Real multi-source ESG report ingestion pipeline with:
- **Authentic HTTP:** SEC EDGAR API + Company IR downloads (no mocks)
- **Determinism Proof:** 3-run identical SHA256 hash validation
- **Fail-Closed:** Explicit error handling on all blockers
- **Honest Status:** Clear stubs for evidence/parity gates (not fake passing)

## What This Is NOT

- ❌ NOT ready for production evidence extraction (Phase 2 needed)
- ❌ NOT enforcing parity constraints (Phase 2 needed)
- ❌ NOT RD source audit (Phase 2 needed)

## Quick Reference

### 1. Check Configuration
```bash
cat configs/companies_live.yaml
```

Edit to add real PDF URLs (or use SEC CIK env vars)

### 2. Fetch Pass (Real Downloads)
```bash
ALLOW_NETWORK=true make live.fetch
# Output: data/raw/org_id=*/year=*/*.pdf
#         artifacts/ingestion/ingestion_summary.json
```

### 3. Replay Pass (Determinism 3×)
```bash
unset ALLOW_NETWORK
make live.replay
# Output: artifacts/matrix/*/baseline/determinism_report.json
#         artifacts/matrix/*/baseline/run_{1,2,3}/output.json|hash.txt
```

### 4. Review Results
```bash
cat artifacts/matrix/matrix_contract.json
# Shows: status (ok/revise), determinism_pass (true/false)
```

### 5. Full Pipeline (One Command)
```bash
ALLOW_NETWORK=true make live.all
# Runs: fetch → replay → contract → summary
```

## Important Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `ALLOW_NETWORK` | Enable/disable real HTTP | `true` or unset |
| `SEED` | Determinism lock | `42` (locked) |
| `PYTHONHASHSEED` | Python hash randomization | `0` (locked) |
| `SEC_USER_AGENT` | SEC API identification | `"ESG-Scoring/1.0 (contact=...)"` |
| `SEC_RPS_DELAY` | SEC rate limiting | `1.0` (seconds) |
| `CIK_APPLE_INC` | SEC CIK lookup (instead of override URL) | `0000320193` |

## Output Structure

```
data/
├── raw/org_id={company}/year={year}/
│   └── {doc_id}.pdf              # Cached documents from fetch pass
└── silver/org_id={company}/year={year}/
    └── {doc_id}_chunks.jsonl     # Extracted chunks (stubs)

artifacts/
├── ingestion/
│   ├── org_id={company}/year={year}/
│   │   └── ingestion_manifest.json  # Per-doc manifest (source_url, sha256, fetched_at)
│   └── ingestion_summary.json       # Fetch pass summary (documents[], blocked[])
└── matrix/
    ├── {doc_id}/baseline/
    │   ├── run_1/output.json|hash.txt   # Determinism run 1
    │   ├── run_2/output.json|hash.txt   # Determinism run 2
    │   ├── run_3/output.json|hash.txt   # Determinism run 3
    │   └── determinism_report.json      # Hashes identical: true/false
    ├── {doc_id}/pipeline_validation/
    │   ├── evidence_audit.json          # Stub (Phase 2: real extraction)
    │   ├── demo_topk_vs_evidence.json   # Stub (Phase 2: real retrieval)
    │   └── rd_sources.json              # Stub (Phase 2: evidence analysis)
    ├── {doc_id}/output_contract.json    # Per-doc contract
    └── matrix_contract.json             # Summary (status, determinism_pass)
```

## Gate Status

| Gate | Status | Evidence |
|------|--------|----------|
| Authenticity | PASS | Real HTTP requests via requests.Session |
| Determinism | PASS | 3-run identical SHA256 hashes |
| Traceability | PASS | Full HTTP manifests (source_url, headers, sha256, timestamp) |
| Evidence | STUB | Placeholder evidence_audit.json |
| Parity | STUB | Placeholder demo_topk_vs_evidence.json |
| RD Sources | STUB | Empty rd_sources.json |

## Troubleshooting

### "ALLOW_NETWORK must be true"
```bash
# FIX: Set before running fetch pass
export ALLOW_NETWORK=true
make live.fetch
```

### "No CIK found for {company}"
```bash
# Option A: Add override URL to configs/companies_live.yaml
#   url: "https://example.com/path/to/apple_10k_2024.pdf"

# Option B: Set CIK env var
#   export CIK_APPLE_INC=0000320193
#   export CIK_MICROSOFT_CORPORATION=0000789019
```

### "Override URL must end with .pdf"
Ensure override URLs point to actual PDF files, not HTML pages.

### Documents marked "blocked" in summary
Check `artifacts/ingestion/ingestion_summary.json` for error reasons:
```bash
jq '.blocked' artifacts/ingestion/ingestion_summary.json
```

### Determinism check FAIL (hashes differ)
Check if SEED/PYTHONHASHSEED are locked:
```bash
echo "SEED=$SEED PYTHONHASHSEED=$PYTHONHASHSEED"
# Should show: SEED=42 PYTHONHASHSEED=0
```

## Files You Need to Know

| File | Purpose |
|------|---------|
| `agents/crawler/providers/sec_edgar.py` | SEC EDGAR HTTP client (real) |
| `agents/crawler/providers/company_ir.py` | Company IR HTTP client (real, robots-aware) |
| `scripts/ingest_live_matrix.py` | Fetch pass orchestrator (ALLOW_NETWORK=true) |
| `scripts/run_matrix.py` | Replay pass orchestrator (determinism 3×) |
| `configs/companies_live.yaml` | Configuration (edit override URLs here) |
| `Makefile` | Pipeline targets (live.fetch, live.replay, etc.) |

## What Comes Next (Phase 2)

1. **PDF Extraction:** enhanced_pdf_extractor with page tracking
2. **Evidence Gate:** Validate ≥2 pages per theme
3. **Parity Gate:** Real topk retrieval + subset validation
4. **RD Audit:** Evidence analysis for renewable/distributed energy
5. **Full QA:** Coverage, mypy --strict, interrogate, lizard gates

## Technical Details

### Real HTTP Clients
- **SecEdgarClient:** Uses SEC API (data.sec.gov) for ticker resolution + filing listing
- **CompanyIRClient:** Uses requests + robots.txt parser for IR downloads
- Both: Full HTTP manifests (source_url, request/response headers, SHA256, timestamp)

### Determinism
- SEED=42, PYTHONHASHSEED=0 locks all randomness
- 3-run identical hash proof via sha256(output.json bytes)
- Real timestamps in HTTP manifests (not fixed)

### Fail-Closed
- ALLOW_NETWORK check (fetch) / unset check (replay)
- Missing config files → exit(1)
- Network errors → marked "blocked"
- Determinism failures → status="revise"

## Support

For issues or questions, see:
- `tasks/TASK-001-LIVE-INGESTION-AUTHENTICITY.md` - Full specification
- `Makefile` - run `make live.authentic-runbook` for detailed instructions
