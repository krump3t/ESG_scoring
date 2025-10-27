# Real-Data E2E Demo Plan (Demo B)

Owner: ESG Scoring Team  
Audience: Engineering, QA, DevOps, Stakeholders  
Scope: Online end‑to‑end run using real sources (SEC EDGAR primary), producing bronze/silver Parquet, retrieval artifacts, rubric scores, and live API responses.

---

## Objectives
- Demonstrate real‑world ingestion, extraction, normalization, retrieval, scoring, and serving over a US public company’s 10‑K.
- Produce audit‑ready artifacts (Parquet, DuckDB, evidence CSV) and operational telemetry (logs, metrics).
- Validate determinism toggles, rate‑limits, and fallbacks under network variability.

---

## Architecture Overview (Components)
- Providers (ingestion):
  - `agents/crawler/data_providers/sec_edgar_provider.py: SECEdgarProvider`
  - `agents/crawler/data_providers/ticker_lookup.py: TickerLookupProvider`
  - Optional: `agents/crawler/data_providers/cdp_provider.py` (ancillary)
- Extraction (unstructured + structured):
  - HTML/PDF evidence: `agents/crawler/extractors/enhanced_pdf_extractor.py`
  - Pattern matchers: `agents/parser/matchers/*`
  - Evidence model: `agents/parser/models.py: Evidence`
  - SEC CompanyFacts (structured metrics): `agents/extraction/structured_extractor.py`
- Storage & normalization:
  - Bronze writer: `agents/storage/bronze_writer.py`
  - Silver normalizer: `agents/storage/silver_normalizer.py`
  - DuckDB views: `agents/storage/duckdb_manager.py`
- Retrieval & embeddings:
  - Parquet/Hybrid retrievers: `libs/retrieval/*`
  - Embedders: `libs/retrieval/embeddings/*`
  - Optional vector backend: `libs/retrieval/vector_backends/astradb_store.py`
- Scoring & reporting:
  - Rubric loader: `agents/scoring/rubric_loader.py`
  - Scorer (v3): `agents/scoring/rubric_v3_scorer.py`
  - Evidence table: `agents/scoring/evidence_table_generator.py`
- API:
  - FastAPI app: `apps/api/main.py` (endpoints: `/health`, `/ready`, `/live`, `/metrics`, `/score`)

---

## Requirements

### Software
- Python (3.10+ recommended)
- Install deps: `pip install -r requirements.txt`
- Optional CLIs: `uvicorn` (installed via requirements), `duckdb` shell (optional)

### Hardware
- CPU: 2+ cores recommended
- RAM: 4–8 GB (10‑K processing), more for large filings
- Disk: 2+ GB free for Parquet and caches

### Network
- Outbound HTTPS to:
  - `https://data.sec.gov`, `https://www.sec.gov` (SEC EDGAR)
  - Optional: `https://data.cdp.net` (CDP Open Data)
  - Optional: IBM Cloud (watsonx.ai) and AstraDB endpoints if enabled

### Credentials & Env Vars (optional)
- Watsonx (if semantic/LLM):
  - `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_REGION` (default `us-south`)
- AstraDB (if vector store):
  - `ASTRA_DB_API_ENDPOINT`, `ASTRA_DB_TOKEN`, `ASTRA_DB_KEYSPACE`
- Determinism toggles (optional):
  - `SEED=42`, `PYTHONHASHSEED=0`

### Paths & Dirs
- Ensure writable:
  - `data/pdf_cache`
  - `data/bronze`, `data/silver`
  - `artifacts/` (for reports/previews)

### Compliance
- SEC User‑Agent must include contact email.
- Respect SEC rate limit: max 10 req/sec; provider enforces retries/backoff.

---

## Configuration

### Data Source Registry
- File: `configs/data_source_registry.json`
- Ensure entries for `sec_edgar` are present and priority is set appropriately.

### Integration Flags
- File: `configs/integration_flags.json`
- Suggested demo settings:
  - `"semantic_enabled": false` (enable later if Watsonx creds available)
  - `"watsonx_enabled": false`
  - `"astradb_enabled": false`

### Provider Parameters
- SECEdgarProvider:
  - Provide `user_agent` with contact email (e.g., `ESG-Research/1.0 (team@example.com)`) when instantiating.

---

## Run Modes
- Minimal (recommended): SEC → HTML text → Evidence → Bronze → Silver → Rubric scoring → API.
- Enriched: Add embeddings (DeterministicEmbedder or Watsonx) + hybrid retrieval.
- Structured: Mix in CompanyFacts via `StructuredExtractor` if JSON available locally.

---

## End‑to‑End Workflow

### Phase 0 — Pre‑Flight Checks
- Verify internet access to SEC hosts.
- Validate `configs/data_source_registry.json` and integration flags.
- Create required directories if missing.
- Sanity check Python env: `python -c "import duckdb, pyarrow, fastapi"`

### Phase 1 — Acquire Filing (SEC 10‑K)
- Resolve CIK (if needed) via `TickerLookupProvider`.
- Fetch 10‑K using `SECEdgarProvider.fetch_10k(cik, fiscal_year)`
  - Output: dict with `raw_html`, `raw_text`, `company_name`, `filing_date`, `content_sha256`, `source_url`.
  - Class: `agents/crawler/data_providers/sec_edgar_provider.py: SECEdgarProvider`

Example (Python REPL/driver):
```python
from agents.crawler.data_providers.sec_edgar_provider import SECEdgarProvider
provider = SECEdgarProvider(user_agent="ESG-Research/1.0 (team@example.com)")
filing = provider.fetch_10k(cik="0000320193", fiscal_year=2023)  # Apple Inc.
```

### Phase 2 — Extract Evidence (Unstructured)
- From `filing["raw_text"]`, run matchers to detect ESG themes and context windows.
  - Matchers: `agents/parser/matchers/*` (e.g., `ghg_matcher.py`)
  - Build `Evidence` objects: `agents/parser/models.py: Evidence`

Optional (PDF path): Use `EnhancedPDFExtractor` for PDFs and then classify.

### Phase 3 — Persist to Bronze (Parquet)
- Use `BronzeEvidenceWriter` to write Evidence with Hive partitioning.
  - Schema: `agents/storage/bronze_writer.py: EVIDENCE_SCHEMA`
  - Partitions: `data/bronze/org_id=<ORG>/year=<YYYY>/theme=<THEME>/*.parquet`

### Phase 4 — Normalize to Silver
- Deduplicate and apply freshness penalty via `SilverNormalizer.normalize_bronze_to_silver()`.
  - Output: `data/silver/.../*.parquet` with `adjusted_confidence` and `is_most_recent`.

### Phase 5 — Retrieval (Lexical + Optional Semantic)
- Minimal: `libs/retrieval/parquet_retriever.py` to search Silver.
- Hybrid (optional): `libs/retrieval/hybrid_retriever.py` with Deterministic or Watsonx embeddings.
- Optional vector backend: `libs/retrieval/vector_backends/astradb_store.py`.

### Phase 6 — Rubric Scoring & Report
- Load rubric: `agents/scoring/rubric_loader.py`
- Score: `agents/scoring/rubric_v3_scorer.py`
- Generate evidence table CSV: `agents/scoring/evidence_table_generator.py`

### Phase 7 — Serve API
- App: `apps/api/main.py` (FastAPI)
- Endpoints:
  - Health: `/health`, `/ready`, `/live`
  - Metrics: `/metrics`
  - Scoring: `/score`

### Phase 8 — Validate & Archive
- DuckDB queries via `agents/storage/duckdb_manager.py` to validate counts.
- Archive outputs under `artifacts/`.

---

## Execution Blueprint (Commands & Snippets)

Note: Replace placeholders like `AAPL`, `0000320193`, `2023` accordingly.

### 1) Fetch Real Report(s)
- Script (real company fetch helpers): `fetch_real_reports.py`
- Or invoke provider directly (see Phase 1 example).

### 2) Evidence Extraction → Bronze
- Write a short driver or reuse scripts that produce `Evidence`:
```python
from agents.parser.models import Evidence
from agents.storage.bronze_writer import BronzeEvidenceWriter
from datetime import datetime, UTC
from pathlib import Path

org_id, year, theme = "AAPL", 2023, "GHG"
# Build evidence_list from matchers over filing["raw_text"]
writer = BronzeEvidenceWriter(base_path=Path("data/bronze"))
writer.write_evidence_batch(evidence_list, ingestion_id=f"demo_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}")
```

### 3) Normalize → Silver
```python
from agents.storage.silver_normalizer import SilverNormalizer
from pathlib import Path

normalizer = SilverNormalizer(
  db_path=Path("data/evidence.duckdb"),
  bronze_path=Path("data/bronze"),
  silver_path=Path("data/silver"),
)
normalizer.normalize_bronze_to_silver()
```

### 4) Quick Validation (DuckDB)
```python
from agents.storage.duckdb_manager import DuckDBManager, create_bronze_view
from pathlib import Path

mgr = DuckDBManager(db_path=Path("data/evidence.duckdb"), bronze_path=Path("data/bronze"))
with mgr.get_connection() as con:
    create_bronze_view(con, Path("data/bronze"))
    rows = con.execute("""
        SELECT theme, COUNT(*) AS n
        FROM bronze_evidence
        WHERE org_id = 'AAPL' AND year = 2023
        GROUP BY theme ORDER BY n DESC
    """).fetchall()
    print(rows)
```

### 5) Optional: Embeddings & Hybrid Retrieval
- Deterministic (offline): `libs/retrieval/embeddings/deterministic_embedder.py`
- Watsonx (online): `libs/retrieval/embeddings/watsonx_embedder.py`

### 6) Scoring & Evidence Table
```python
from agents.scoring.rubric_loader import RubricLoader
from agents.scoring.rubric_v3_scorer import RubricV3Scorer
from agents.scoring.evidence_table_generator import EvidenceTableGenerator
from pathlib import Path

rubric = RubricLoader().load_from_markdown(Path("rubrics/compile_rubric.md"))  # adjust path if needed
scorer = RubricV3Scorer(rubric)
# Provide retrieved evidence per theme to scorer (from Silver/Hybrid retrieval)
scores = scorer.score_company("Apple Inc.", 2023, evidence_by_theme)

etable = EvidenceTableGenerator().generate(scores)
etable.to_csv("artifacts/evidence_table.csv", index=False)
```

### 7) API: Run & Test
- Run API: `uvicorn apps.api.main:app --host 0.0.0.0 --port 8000`
- Health: `GET http://localhost:8000/health`
- Score:
```bash
curl -s -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{"company":"Apple Inc.","year":2023,"query":"ESG maturity assessment"}' | jq
```
- Metrics: `GET http://localhost:8000/metrics`

---

## Expected Artifacts & Layout
- Bronze Parquet: `data/bronze/org_id=AAPL/year=2023/theme=GHG/*.parquet`
- Silver Parquet: `data/silver/org_id=AAPL/year=2023/theme=GHG/*.parquet`
- DuckDB file: `data/evidence.duckdb`
- Evidence CSV: `artifacts/evidence_table.csv`
- Logs: Structured logs from extraction/normalization/scoring/API
- Metrics: Prometheus exposition at `/metrics`

---

## Acceptance Criteria
- SEC 10‑K fetched successfully with valid User‑Agent.
- Non‑empty evidence written to Bronze for at least one theme.
- Silver contains deduped entries with `adjusted_confidence` in [0, 1].
- DuckDB query returns evidence counts for target org/year.
- Scoring returns per‑theme stages and overall confidence; evidence table generated.
- API responds to `/health`, `/metrics`, and `/score` with a valid schema.

---

## Observability & QA
- Logs:
  - Provider fetch success/fail, retries, rate limiting events.
  - Extraction findings count, write paths, processing times.
- Metrics (apps/api/metrics.py):
  - Request counters by route/method/status.
  - Latency histograms for scoring.
  - Gauges for active connections (if enabled).

---

## Troubleshooting
- 503 / Rate limit:
  - Verify 10 req/sec; confirm User‑Agent includes email; retry/backoff is enabled.
- Empty evidence:
  - Ensure correct matchers; verify `raw_text` contains expected sections (e.g., Item 1A).
- Parquet schema mismatch:
  - Ensure Bronze schema is consistent; avoid ad‑hoc fields mid‑run.
- Silver no files found:
  - Verify Bronze path and partitions; ensure DuckDB glob reads files.
- API errors:
  - Check FastAPI logs; validate request schema; ensure scoring pipeline is wired to read Silver.

---

## Risks & Mitigations
- Source availability: Use retries and fallbacks (Ticker → SEC retry).
- Large filings: Process in segments; avoid loading entire doc if memory constrained.
- External integrations: Keep semantic/Watsonx optional; start minimal.

---

## Timeline (Single Demo Run)
- Prep & config: 15–30 min
- Fetch & extract: 2–10 min (size dependent)
- Normalize & retrieval prep: 1–5 min
- Scoring & API: 1–5 min
- Validation & artifacts: 5–15 min

---

## Checklists

### Pre‑Flight
- [ ] Deps installed
- [ ] Directories exist (`data/*`, `artifacts/`)
- [ ] SEC User‑Agent configured
- [ ] Integration flags set
- [ ] Network to SEC endpoints verified

### Post‑Run
- [ ] Bronze and Silver populated
- [ ] DuckDB evidence count sane
- [ ] Evidence CSV generated
- [ ] API `/score` returns valid response
- [ ] Logs show no unhandled errors

---

## Appendices

### A. Sample ScoreRequest (POST /score)
```json
{
  "company": "Apple Inc.",
  "year": 2023,
  "query": "ESG maturity assessment"
}
```

### B. Sample DuckDB Validation Queries
```sql
-- Evidence by theme
SELECT theme, COUNT(*) AS n
FROM bronze_evidence
WHERE org_id = 'AAPL' AND year = 2023
GROUP BY theme ORDER BY n DESC;

-- Top quotes by confidence
SELECT theme, page_no, LEFT(extract_30w, 200) AS quote, confidence
FROM bronze_evidence
WHERE org_id = 'AAPL' AND year = 2023
ORDER BY confidence DESC
LIMIT 20;
```

### C. Notes on Determinism
- For reproducibility in demos:
  - Use `DeterministicEmbedder` if embeddings are needed.
  - Fix random seeds via env; prefer cached responses for any LLM steps.
