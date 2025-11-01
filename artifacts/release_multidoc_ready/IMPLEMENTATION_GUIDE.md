# Multi-Document E2E Implementation Guide
## Step-by-Step Scale-Up from Single-Doc to Multi-Doc Matrix

**Date**: 2025-10-28
**For**: Development Team
**Prerequisites**: Single-doc validation complete (msft_2023)
**Goal**: Execute full multi-doc E2E workflow with Evidence gate

---

## Quick Start (Option 1: Use Available PDFs)

**Estimated Time**: 3-4 hours
**Data Source**: Local PDFs in pdf_cache/
**Confidence**: HIGH (infrastructure validated)

### Step 1: Update Configuration (5 min)

Edit `configs/companies_live.yaml`:

```yaml
companies:
  - name: "Microsoft Corporation"
    ticker: "MSFT"
    year: 2023
    doc_id: "msft_2023"
    provider: "local"
    local_path: "data/silver/org_id=MSFT"  # Already processed

  - name: "Apple Inc."
    ticker: "AAPL"
    year: 2023
    doc_id: "apple_2023"
    provider: "local"
    local_path: "data/pdf_cache/Apple_2023_sustainability.pdf"

  - name: "ExxonMobil Corporation"
    ticker: "XOM"
    year: 2023
    doc_id: "exxonmobil_2023"
    provider: "local"
    local_path: "data/pdf_cache/ExxonMobil_2023_sustainability.pdf"

  - name: "JPMorgan Chase & Co."
    ticker: "JPM"
    year: 2023
    doc_id: "jpmorgan_2023"
    provider: "local"
    local_path: "data/pdf_cache/JPMorgan_Chase_2023_esg.pdf"
```

### Step 2: Data Ingestion (2-3 hours)

```bash
cd "prospecting-engine"

# Set environment
export WX_API_KEY="<your-watsonx-api-key>"
export WX_PROJECT="<your-watsonx-project-id>"
export SEED=42 PYTHONHASHSEED=0 ALLOW_NETWORK=true

# Ingest Apple
python scripts/ingest_single_doc.py \
    --pdf "data/pdf_cache/Apple_2023_sustainability.pdf" \
    --doc-id "apple_2023" \
    --company "Apple Inc." \
    --year 2023

# Ingest ExxonMobil
python scripts/ingest_single_doc.py \
    --pdf "data/pdf_cache/ExxonMobil_2023_sustainability.pdf" \
    --doc-id "exxonmobil_2023" \
    --company "ExxonMobil Corporation" \
    --year 2023

# Ingest JPMorgan
python scripts/ingest_single_doc.py \
    --pdf "data/pdf_cache/JPMorgan_Chase_2023_esg.pdf" \
    --doc-id "jpmorgan_2023" \
    --company "JPMorgan Chase & Co." \
    --year 2023

# Verify silver data created
ls -R data/silver/org_id=AAPL/
ls -R data/silver/org_id=XOM/
ls -R data/silver/org_id=JPM/
```

**Expected**: 50-200 parquet chunks per document

### Step 3: Build Semantic Indices (15-30 min)

```bash
export WX_OFFLINE_REPLAY=false ALLOW_NETWORK=true

# Build indices for new docs
for doc_id in apple_2023 exxonmobil_2023 jpmorgan_2023; do
    echo "Building index for $doc_id..."
    python scripts/semantic_fetch_replay.py \
        --phase fetch \
        --doc-id $doc_id
done

# Verify indices created
ls -lh data/index/apple_2023/
ls -lh data/index/exxonmobil_2023/
ls -lh data/index/jpmorgan_2023/
```

**Expected**:
- `chunks.parquet` (chunk metadata)
- `embeddings.bin` (768-dim vectors)
- `meta.json` (model info)

### Step 4: Offline REPLAY 3× (5 min)

```bash
unset ALLOW_NETWORK
export WX_OFFLINE_REPLAY=true SEED=42 PYTHONHASHSEED=0

mkdir -p artifacts/multidoc_matrix/run_{1,2,3}

for i in 1 2 3; do
    echo "=== REPLAY $i/3 ==="
    python scripts/run_matrix.py \
        --config configs/companies_live.yaml \
        --semantic \
        > artifacts/multidoc_matrix/run_$i/output.log 2>&1
done
```

**Expected**: 3 identical output logs

### Step 5: Compute Determinism Hashes (1 min)

```bash
for i in 1 2 3; do
    sha256sum artifacts/multidoc_matrix/run_$i/output.log
done
```

**Expected**: All 3 hashes identical

### Step 6: Validate Authenticity Gates (1 min)

```bash
python - <<'PY'
import json, glob, sys

ok = True
msgs = []

# Determinism per doc
for f in glob.glob("artifacts/matrix/*/baseline/determinism_report.json"):
    d = json.load(open(f, encoding="utf-8"))
    if not d.get("identical") or len(set(d.get("hashes", []))) != 1:
        ok = False
        msgs.append(f"[determinism FAIL] {f}")
    else:
        msgs.append(f"[determinism PASS] {f}")

# Parity per doc
for f in glob.glob("artifacts/matrix/*/pipeline_validation/demo_topk_vs_evidence.json"):
    d = json.load(open(f, encoding="utf-8"))
    if not d.get("subset_ok", False):
        ok = False
        msgs.append(f"[parity FAIL] {f}")
    else:
        msgs.append(f"[parity PASS] {f}")

# Evidence per doc (NEW)
for f in glob.glob("artifacts/matrix/*/pipeline_validation/evidence_audit.json"):
    d = json.load(open(f, encoding="utf-8"))
    doc_ok = True
    for theme, info in d.items():
        if isinstance(info, dict):
            if info.get("quotes_count", 0) < 2 or info.get("pages_count", 0) < 2:
                ok = False
                doc_ok = False
                msgs.append(f"[evidence FAIL] {f} :: {theme}")
    if doc_ok:
        msgs.append(f"[evidence PASS] {f}")

# Cache posture
online_calls = 0
for line in open("artifacts/wx_cache/ledger.jsonl", encoding="utf-8"):
    try:
        row = json.loads(line)
        if row.get("phase") == "replay" and row.get("online") is True:
            online_calls += 1
    except:
        pass

if online_calls > 0:
    ok = False
    msgs.append(f"[cache FAIL] {online_calls} online calls during replay")
else:
    msgs.append("[cache PASS] Zero online calls")

print("=" * 70)
print("MULTI-DOC AUTHENTICITY GATES")
print("=" * 70)
for msg in msgs:
    print(msg)
print()
print("Overall Status:", "PASS" if ok else "FAIL")
print("=" * 70)

sys.exit(0 if ok else 1)
PY
```

**Expected**: All gates PASS

### Step 7: Generate NL Reports (10-15 min)

```bash
for doc_id in msft_2023 apple_2023 exxonmobil_2023 jpmorgan_2023; do
    echo "Generating report for $doc_id..."
    python scripts/generate_nl_report.py \
        --doc-id $doc_id \
        --output "artifacts/reports/${doc_id}_nl_report.md"
done

# List generated reports
ls -lh artifacts/reports/*_nl_report.md
```

**Expected**: 4 NL reports with grounded evidence

### Step 8: Assemble Release Pack (1 min)

```bash
python scripts/assemble_release_pack.py \
    --output artifacts/release_multidoc_final
```

**Expected**: `artifacts/release_multidoc_final/`
- ATTESTATION_MANIFEST.json
- INDEX.txt
- 4× determinism_report.json
- 4× demo_topk_vs_evidence.json
- 4× evidence_audit.json
- 4× nl_report.md
- matrix_contract.json
- wx_ledger.jsonl

---

## Alternative: Implement Providers (Option 2)

**Estimated Time**: 1-2 days
**Data Source**: SEC EDGAR, Company IR websites
**Confidence**: MEDIUM (requires new code)

### Step 1: Implement SEC EDGAR Provider

Create `libs/providers/sec_edgar_provider.py`:

```python
from typing import Dict, Optional
import requests
from pathlib import Path

class SecEdgarProvider:
    """Fetch 10-K filings from SEC EDGAR."""

    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self.base_url = "https://www.sec.gov/cgi-bin/browse-edgar"

    def fetch_10k(
        self,
        ticker: str,
        year: int,
        output_dir: Path
    ) -> Dict[str, str]:
        """
        Fetch 10-K filing for ticker in given year.

        Returns:
            {
                "pdf_path": str,
                "filing_date": str,
                "accession_number": str,
                "source_url": str
            }
        """
        # 1. Lookup CIK from ticker
        cik = self._lookup_cik(ticker)

        # 2. Find 10-K filing for year
        filing = self._find_10k(cik, year)

        # 3. Download filing as PDF
        pdf_path = self._download_filing(filing, output_dir)

        return {
            "pdf_path": str(pdf_path),
            "filing_date": filing["filing_date"],
            "accession_number": filing["accession_number"],
            "source_url": filing["url"]
        }

    def _lookup_cik(self, ticker: str) -> str:
        # Implementation: Use SEC ticker lookup API
        pass

    def _find_10k(self, cik: str, year: int) -> Dict:
        # Implementation: Query EDGAR for 10-K in fiscal year
        pass

    def _download_filing(self, filing: Dict, output_dir: Path) -> Path:
        # Implementation: Download and save PDF
        pass
```

### Step 2: Implement Company IR Provider

Create `libs/providers/company_ir_provider.py`:

```python
from typing import Dict
import requests
from pathlib import Path

class CompanyIRProvider:
    """Download PDFs from company investor relations websites."""

    def fetch_pdf(
        self,
        url: str,
        output_dir: Path,
        doc_id: str
    ) -> Dict[str, str]:
        """
        Download PDF from direct URL.

        Returns:
            {
                "pdf_path": str,
                "source_url": str,
                "content_length": int,
                "sha256": str
            }
        """
        # Download with proper user agent
        response = requests.get(url, headers={
            "User-Agent": "IBM-ESG/ScoringApp/0.1 (Contact: ...)"
        })

        # Save PDF
        pdf_path = output_dir / f"{doc_id}.pdf"
        pdf_path.write_bytes(response.content)

        # Compute hash
        import hashlib
        sha256 = hashlib.sha256(response.content).hexdigest()

        return {
            "pdf_path": str(pdf_path),
            "source_url": url,
            "content_length": len(response.content),
            "sha256": sha256
        }
```

### Step 3: Update Ingestion Orchestrator

Edit `scripts/ingest_live_matrix.py`:

```python
from libs.providers.sec_edgar_provider import SecEdgarProvider
from libs.providers.company_ir_provider import CompanyIRProvider

class IngestionOrchestrator:
    def __init__(self, config_path: str):
        self.sec_edgar = SecEdgarProvider(
            user_agent=os.getenv("SEC_USER_AGENT")
        )
        self.company_ir = CompanyIRProvider()
        # ...

    def _download_or_locate_pdf(self, company: Dict, output_dir: Path):
        provider = company.get("provider")

        if provider is None:
            # Auto-route: try SEC EDGAR first
            if company.get("region") == "US":
                return self.sec_edgar.fetch_10k(
                    company["ticker"],
                    company["year"],
                    output_dir
                )

        elif provider == "sec_edgar":
            return self.sec_edgar.fetch_10k(
                company["ticker"],
                company["year"],
                output_dir
            )

        elif provider == "company_ir":
            return self.company_ir.fetch_pdf(
                company["direct_url"],
                output_dir,
                company["doc_id"]
            )

        elif provider == "local":
            # Existing logic
            pass

        else:
            raise ValueError(f"Unknown provider: {provider}")
```

### Step 4: Test Provider Implementation

```bash
# Test SEC EDGAR
python -c "
from libs.providers.sec_edgar_provider import SecEdgarProvider
provider = SecEdgarProvider('IBM-ESG/ScoringApp/0.1')
result = provider.fetch_10k('MSFT', 2024, Path('data/raw'))
print(result)
"

# Test Company IR
python -c "
from libs.providers.company_ir_provider import CompanyIRProvider
provider = CompanyIRProvider()
result = provider.fetch_pdf(
    'https://www.unilever.com/.../sustainability-report-2023.pdf',
    Path('data/raw'),
    'unilever_2023'
)
print(result)
"
```

### Step 5: Run Full Workflow

Follow Option 1 steps 2-8, but with provider-fetched data.

---

## Validation Checklist

Before declaring multi-doc E2E complete, verify:

### Pre-FETCH
- [ ] Config has 3-5 real companies
- [ ] Each company has valid data source (local PDF or provider)
- [ ] WX_API_KEY and WX_PROJECT set
- [ ] SEED=42, PYTHONHASHSEED=0

### Post-FETCH
- [ ] Silver data exists for all companies (`data/silver/org_id=<ORG>`)
- [ ] Each company has ≥50 chunks
- [ ] Semantic indices built (`data/index/<doc_id>/`)
- [ ] Each index has ≥50 embeddings
- [ ] Cache ledger shows online calls (`artifacts/wx_cache/ledger.jsonl`)

### Post-REPLAY
- [ ] 3 run logs exist (`artifacts/multidoc_matrix/run_{1,2,3}/output.log`)
- [ ] All 3 logs have identical SHA256 hash
- [ ] Per-doc artifacts exist:
  - [ ] `artifacts/matrix/<doc_id>/baseline/determinism_report.json`
  - [ ] `artifacts/matrix/<doc_id>/pipeline_validation/demo_topk_vs_evidence.json`
  - [ ] `artifacts/matrix/<doc_id>/pipeline_validation/evidence_audit.json`
  - [ ] `artifacts/matrix/<doc_id>/output_contract.json`
- [ ] Matrix contract exists: `artifacts/matrix/matrix_contract.json`
- [ ] Cache ledger shows NO online calls during replay phase

### Gates Validation
- [ ] Determinism: All docs have `identical: true`
- [ ] Parity: All docs have `subset_ok: true`
- [ ] Evidence: All docs have ≥2 quotes from ≥2 pages per theme
- [ ] Cache: Zero `online: true` entries with `phase: replay`

### Reports
- [ ] NL report exists for each company
- [ ] Each report has ≥2 themes
- [ ] Each theme has ≥2 verbatim quotes (≥6 words)
- [ ] Each quote has page number + source attribution

### Release Pack
- [ ] `artifacts/release_multidoc_final/` exists
- [ ] ATTESTATION_MANIFEST.json present
- [ ] All determinism reports included
- [ ] All parity reports included
- [ ] All evidence audits included
- [ ] All NL reports included
- [ ] Matrix contract included
- [ ] Cache ledger included

---

## Troubleshooting

### Issue: FETCH fails with provider error

**Symptoms**: `RuntimeError: Provider 'None' not implemented`

**Solution**:
1. Set `provider: "local"` in config
2. Or implement provider (see Option 2)

### Issue: Evidence gate fails

**Symptoms**: `[evidence FAIL] ... :: GHG`

**Root Cause**: Document has <2 quotes or <2 pages for theme

**Solution**:
1. Check chunk count: `ls data/silver/org_id=<ORG>/year=<YEAR>/theme=<THEME>/*.parquet | wc -l`
2. If <2 chunks, reduce `chunk_size` in `configs/extraction.json`
3. If chunks span only 1 page, use longer document

### Issue: Determinism hash mismatch

**Symptoms**: Run 1, 2, 3 have different hashes

**Root Cause**: Nondeterministic component in pipeline

**Solution**:
1. Check SEED=42, PYTHONHASHSEED=0 set
2. Check WX_OFFLINE_REPLAY=true during REPLAY
3. Check cache ledger for online calls
4. Remove timestamps/UUIDs from output payloads

### Issue: Cache miss during REPLAY

**Symptoms**: `RuntimeError: Cache miss in offline replay mode`

**Root Cause**: FETCH phase incomplete or cache cleared

**Solution**:
1. Re-run FETCH phase for affected doc_id
2. Check cache dir: `ls artifacts/wx_cache/embeddings/`
3. Check ledger: `tail artifacts/wx_cache/ledger.jsonl`

---

## Success Criteria

Multi-doc E2E is complete when:

1. ✓ 3-5 real companies processed
2. ✓ REPLAY 3× produces identical hashes
3. ✓ All gates PASS (determinism, parity, evidence, cache)
4. ✓ NL reports generated for all companies
5. ✓ Release pack assembled with attestation

**Estimated Total Time**: 3-4 hours (Option 1) or 1-2 days (Option 2)

**Confidence**: HIGH (infrastructure validated, path proven)

---

## Contact

For questions or issues:
- Review: `artifacts/MULTI_DOC_READINESS_REPORT.md`
- Check validation: `artifacts/release_multidoc_ready/`
- Consult E2E proof: `artifacts/release_e2e/E2E_COMPLIANCE.md`

---

**Generated**: 2025-10-28T23:10:00Z
**For**: Development Team
**Status**: Ready for implementation
