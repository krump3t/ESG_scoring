# Design: Service Activation & Live Wiring

**Task:** 011-service-activation
**Protocol:** SCA v13.8-MEA
**Date:** 2025-11-19

---

## System Architecture

### Current State (Offline Only)

```
┌─────────────┐
│  API Client │
└──────┬──────┘
       │ POST /score
       ▼
┌─────────────────────┐
│   FastAPI /score    │
│  (apps/api/main.py) │
└──────┬──────────────┘
       │ Always routes to:
       ▼
┌──────────────────────────┐
│   Demo Flow              │
│ (apps/pipeline/demo_flow)│
│   • Offline data only    │
│   • From manifest cache  │
└──────────────────────────┘
```

**Problem:** PipelineOrchestrator exists but is never used. Live ingestion not possible.

---

### Target State (Auto-Detection)

```
┌─────────────┐
│  API Client │
└──────┬──────┘
       │ POST /score
       ▼
┌───────────────────────────────────┐
│      FastAPI /score               │
│   (apps/api/main.py)              │
│   • Checks ALLOW_NETWORK env var  │
└─────────┬─────────────────┬───────┘
          │                 │
    false │                 │ true
          ▼                 ▼
┌──────────────┐    ┌─────────────────────┐
│  Demo Flow   │    │ PipelineOrchestrator│
│   (offline)  │    │     (live)          │
└──────────────┘    └──────┬──────────────┘
                           │ Uses:
                           ▼
                    ┌──────────────────┐
                    │  CrawlerAdapter  │
                    │   (NEW)          │
                    └──────┬───────────┘
                           │ Wraps:
                           ▼
                    ┌──────────────────────┐
                    │ MultiSourceCrawler   │
                    │ • SEC EDGAR Provider │
                    │ • GRI, CDP, SASB     │
                    └──────────────────────┘
```

**Benefits:**
- Offline mode: Deterministic, fast, no network required (CI/CD, demos)
- Online mode: Live data, latest filings, real-world validation

---

## Component Design

### 1. CrawlerAdapter (New Class)

**Location:** `agents/crawler/crawler_adapter.py`

**Purpose:** Bridge incompatible APIs

**Interface:**
```python
class CrawlerAdapter:
    """Adapter: MultiSourceCrawler → PipelineOrchestrator interface"""

    def __init__(self, crawler: MultiSourceCrawler):
        """Initialize with wrapped crawler instance"""
        self._crawler = crawler

    def crawl_company(self, company_cik: str, fiscal_year: int) -> dict:
        """
        Translate orchestrator call to crawler API.

        Args:
            company_cik: SEC CIK number (e.g., "0000320193")
            fiscal_year: Year (e.g., 2024)

        Returns:
            dict: {
                "sec_edgar": [CompanyReport, ...],
                "gri": [...],
                ...
            }

        Raises:
            ValueError: If CIK invalid or company not found
        """
```

**Implementation Details:**

1. **CIK → Company Name Lookup:**
   ```python
   def _cik_to_company_name(self, cik: str) -> str:
       """Use TickerLookupProvider to resolve CIK → name"""
       # Implementation uses agents/crawler/data_providers/ticker_lookup.py
   ```

2. **API Translation:**
   ```python
   def crawl_company(self, company_cik: str, fiscal_year: int) -> dict:
       company_name = self._cik_to_company_name(company_cik)
       results = self._crawler.search_company_reports(
           company_name=company_name,
           year=fiscal_year
       )
       return results  # Already in correct dict format
   ```

3. **Error Handling:**
   - CIK not found → Return empty dict `{}`
   - Network timeout → Log warning, return partial results
   - Invalid year → Raise ValueError

**Test Strategy:**
- Mock MultiSourceCrawler
- Test CIK lookup (valid, invalid, edge cases)
- Test search_company_reports call with correct args
- Test error paths (network fail, invalid CIK)

---

### 2. PipelineOrchestrator Initialization (Modified)

**Location:** `apps/pipeline_orchestrator.py`

**Current Code (Line 96-98):**
```python
# TODO: Initialize with Phase 2 providers (SEC, GRI, CDP)
self.crawler = None  # Placeholder
```

**New Code:**
```python
from agents.crawler.multi_source_crawler import MultiSourceCrawler
from agents.crawler.crawler_adapter import CrawlerAdapter

# Initialize MultiSourceCrawler with registry
crawler_instance = MultiSourceCrawler(
    registry_path=self.config.get("registry_path", "configs/data_source_registry.json"),
    download_dir=self.config.get("download_dir", "data/pdf_cache")
)

# Wrap in adapter for compatible interface
self.crawler = CrawlerAdapter(crawler_instance)
```

**Configuration Extension:**
```python
PROJECT_CONFIG = {
    "paths": {
        "data_lake": "artifacts/data_lake",
        "logs": "artifacts/logs"
    },
    "crawler": {
        "registry_path": "configs/data_source_registry.json",
        "download_dir": "data/pdf_cache"
    }
}
```

**Test Strategy:**
- Verify crawler is not None after initialization
- Mock CrawlerAdapter and verify run_pipeline calls crawl_company
- Integration test: Full pipeline with mocked crawler

---

### 3. API Auto-Detection Routing (Modified)

**Location:** `apps/api/main.py`

**Current Code (Line 155-180):**
```python
@app.post("/score")
async def score(request: ScoreRequest):
    from apps.pipeline import demo_flow
    # ... always uses demo_flow
```

**New Code:**
```python
import os
from apps.pipeline_orchestrator import PipelineOrchestrator
from apps.pipeline import demo_flow

@app.post("/score")
async def score(request: ScoreRequest):
    """
    Score company ESG performance.
    Routes to offline (demo_flow) or online (orchestrator) based on ALLOW_NETWORK.
    """
    allow_network = os.getenv("ALLOW_NETWORK", "false").lower() == "true"

    if allow_network:
        # Live mode: Fetch fresh data from SEC EDGAR
        logger.info(f"Live mode: Using PipelineOrchestrator for {request.company}")
        orchestrator = PipelineOrchestrator(PROJECT_CONFIG)

        try:
            result = orchestrator.run_pipeline(
                company_cik=request.cik,
                fiscal_year=request.year
            )
        except Exception as e:
            logger.error(f"Orchestrator failed: {e}")
            raise HTTPException(status_code=500, detail=f"Live ingestion failed: {str(e)}")

    else:
        # Offline mode: Use cached data from manifest
        logger.info(f"Offline mode: Using demo_flow for {request.company}")

        # (Existing demo_flow logic)
        semantic_enabled = bool(request.semantic)
        result = demo_flow.run_score(
            company_ticker=request.company,
            year=request.year,
            semantic=semantic_enabled
        )

    return result
```

**Logging Enhancement:**
```python
# Add correlation ID for tracing
import uuid
correlation_id = str(uuid.uuid4())
logger.info(f"[{correlation_id}] Mode: {'live' if allow_network else 'offline'}")
```

**Test Strategy:**
- Mock demo_flow and PipelineOrchestrator
- Test ALLOW_NETWORK=false → demo_flow called
- Test ALLOW_NETWORK=true → orchestrator called
- Test error handling (orchestrator fails → 500 error)

---

## Data Strategy

### Input Data

**Offline Mode (demo_flow):**
- Source: `artifacts/demo/companies.json` manifest
- Tier: Bronze (raw) or Silver (normalized)
- Determinism: ✅ Same input → same output

**Online Mode (orchestrator):**
- Source: SEC EDGAR API (live)
- Tier: Fetched → Bronze → Silver → Gold
- Determinism: ❌ Live data changes over time

### Data Splitting

Not applicable for this task (no ML training/validation split required).

### Normalization

Handled by existing Silver tier logic in orchestrator.

### Leakage Guards

- No data leakage concerns (not ML training)
- Offline mode: Cached data prevents live data contamination in tests

---

## Verification Plan

### Unit Tests (TDD)

**CrawlerAdapter:**
```python
def test_adapter_initializes_with_crawler():
    """Verify adapter wraps MultiSourceCrawler correctly"""

def test_adapter_crawl_company_calls_search():
    """Verify adapter translates crawl_company to search_company_reports"""

def test_adapter_handles_invalid_cik():
    """Verify adapter returns empty dict for unknown CIK"""

def test_adapter_translates_results_format():
    """Verify adapter returns dict[str, list[CompanyReport]]"""
```

**PipelineOrchestrator:**
```python
def test_orchestrator_initializes_crawler():
    """Verify self.crawler is not None after init"""

def test_orchestrator_run_pipeline_calls_crawler():
    """Verify run_pipeline calls self.crawler.crawl_company"""
```

**API Routing:**
```python
def test_score_routes_to_demo_flow_when_offline():
    """ALLOW_NETWORK=false → demo_flow.run_score called"""

def test_score_routes_to_orchestrator_when_online():
    """ALLOW_NETWORK=true → orchestrator.run_pipeline called"""

def test_score_handles_orchestrator_failure():
    """Orchestrator error → HTTP 500 with error detail"""
```

### Integration Tests

**Smoke Test Script:**
```bash
# Test 1: Offline mode
export ALLOW_NETWORK=false
curl -X POST http://localhost:8000/score \
     -H "Content-Type: application/json" \
     -d '{"company": "AAPL", "year": 2024, "cik": "0000320193"}'
# Expected: Success (200), logs show "Offline mode: Using demo_flow"

# Test 2: Online mode
export ALLOW_NETWORK=true
curl -X POST http://localhost:8000/score \
     -H "Content-Type: application/json" \
     -d '{"company": "AAPL", "year": 2024, "cik": "0000320193"}'
# Expected: Success (200), logs show "Live mode: Using PipelineOrchestrator"
```

### Determinism Tests

```bash
# Run offline mode 3 times, compare outputs
for i in {1..3}; do
    curl ... > run_$i.json
done

sha256sum run_1.json run_2.json run_3.json
# Expected: All hashes identical
```

---

## Configuration Management

### Environment Variables

| Variable | Default (Old) | Default (New) | Purpose |
|:---------|:--------------|:--------------|:--------|
| ALLOW_NETWORK | false | **true** | Enable live ingestion |
| LIVE_EMBEDDINGS | false | true | Use watsonx for embeddings |

### Configuration Files

**Dockerfile:**
```dockerfile
# OLD: ENV ALLOW_NETWORK=false
# NEW:
ENV ALLOW_NETWORK=true
```

**docker-compose.live.yml:**
```yaml
# OLD: ALLOW_NETWORK: ${ALLOW_NETWORK:-false}
# NEW:
ALLOW_NETWORK: ${ALLOW_NETWORK:-true}
```

**.env.example:**
```bash
# OLD: ALLOW_NETWORK=false
# NEW:
ALLOW_NETWORK=true
```

**Verification Script:**
```python
# tasks/011-service-activation/scripts/verify_config_alignment.py
def check_config_alignment():
    files = {
        "Dockerfile": "ENV ALLOW_NETWORK=true",
        "docker-compose.live.yml": "ALLOW_NETWORK: ${ALLOW_NETWORK:-true}",
        ".env.example": "ALLOW_NETWORK=true"
    }

    for file, expected in files.items():
        content = Path(file).read_text()
        assert expected in content, f"{file} not aligned!"
```

---

## Success Thresholds

| Metric | Threshold | Status |
|:-------|:----------|:-------|
| Adapter test coverage | ≥95% | 🔄 TBD |
| Routing test coverage | ≥95% | 🔄 TBD |
| Type safety (mypy) | 0 errors | 🔄 TBD |
| Config alignment | 100% (4/4 files) | 🔄 TBD |
| Offline determinism | 100% (3/3 runs identical) | 🔄 TBD |
| Online smoke test | ≥1 success | 🔄 TBD |

---

## Rollback Plan

If Task 011 causes issues:

1. **Revert Adapter:**
   ```bash
   git revert <adapter-commit>
   ```

2. **Restore Orchestrator:**
   ```python
   self.crawler = None  # Revert to placeholder
   ```

3. **Restore API:**
   ```python
   # Remove auto-detection, always use demo_flow
   ```

4. **Restore Configs:**
   ```bash
   git checkout -- Dockerfile docker-compose.live.yml .env.example
   ```

**Impact:** System reverts to offline-only mode (Task 010 state)

---

**Design Status:** Ready for Implementation
**Implementation Method:** TDD Red-Green-Refactor
**Estimated LOC:** ~300 lines (adapter + tests + integration)
