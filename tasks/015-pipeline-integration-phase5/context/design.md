# Design Document - Phase 5: End-to-End Pipeline Integration

**Task ID**: 015-pipeline-integration-phase5
**Phase**: 5
**Date**: 2025-10-24
**SCA Protocol**: v13.8-MEA

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│         PipelineOrchestrator (apps/pipeline_orchestrator.py) │
└──────────────┬──────────────────────────────────────────────┘
               │
      ┌────────▼────────┐
      │  Phase 2        │
      │  Crawler        │
      │  (multi_source_ │
      │   crawler_v2.py)│
      │                 │
      │ Input: CIK,Year │
      │ Output: Report  │
      └────────┬────────┘
               │ SHA256 validation
      ┌────────▼────────┐
      │  Phase 3        │
      │  Extractor      │
      │  (extraction_   │
      │   router.py)    │
      │                 │
      │ Input: Report   │
      │ Output:ESGMetric│
      └────────┬────────┘
               │ SHA256 validation
      ┌────────▼──────────┐
      │  Phase 4          │
      │  Writer           │
      │  (parquet_writer) │
      │                   │
      │ Input: ESGMetrics │
      │ Output: Parquet   │
      └────────┬──────────┘
               │
      ┌────────▼──────────┐
      │  Phase 4          │
      │  Reader (DuckDB)  │
      │  (duckdb_reader)  │
      │                   │
      │ Input: Parquet    │
      │ Output: Query result
      └─────────────────────┘
               │
      ┌────────▼──────────┐
      │ IntegrationValidator
      │ (apps/           │
      │  integration_   │
      │  validator.py)   │
      │                  │
      │ • SHA256 checks  │
      │ • Ground truth   │
      │ • Completeness   │
      └──────────────────┘
```

---

## Critical Path File 1: PipelineOrchestrator

**File**: `apps/pipeline_orchestrator.py`
**Lines**: ~150
**Purpose**: Coordinate Phases 2→3→4 with error handling and logging

### Class Definition

```python
class PipelineOrchestrator:
    """Orchestrates end-to-end ESG data pipeline."""

    def __init__(self, project_config: dict):
        """Initialize orchestrator with Phase 2-4 components.

        Args:
            project_config: Config dict with API keys, paths, etc.
        """
        self.crawler = MultiSourceCrawlerV2(project_config)
        self.extractor = ExtractionRouter(project_config)
        self.writer = ParquetWriter(base_path="data_lake/")
        self.reader = DuckDBReader(base_path="data_lake/")
        self.errors = []
        self.metrics = {}

    def run_pipeline(
        self,
        company_cik: str,
        fiscal_year: int,
        log_path: str = "qa/pipeline.log"
    ) -> PipelineResult:
        """Execute complete pipeline for one company.

        Args:
            company_cik: SEC CIK (e.g., "0000320193" for Apple)
            fiscal_year: Fiscal year (e.g., 2024)
            log_path: Log file path

        Returns:
            PipelineResult with success flag, metrics, latencies

        Raises:
            PipelineError: If critical phase fails
        """
        # Implementation details below

    def _phase2_crawl(self, company_cik: str, fiscal_year: int) -> dict:
        """Phase 2: Crawl SEC EDGAR for company report.

        Returns:
            Crawled report dict with content, source URL, timestamp
        """

    def _phase3_extract(self, report: dict) -> ESGMetrics:
        """Phase 3: Extract metrics from report using asymmetric extractor.

        Returns:
            ESGMetrics instance with extracted fields
        """

    def _phase4_write(self, metrics: ESGMetrics, filename: str) -> Path:
        """Phase 4: Write metrics to Parquet file.

        Returns:
            Path to written Parquet file
        """

    def _phase4_query(self, company_name: str) -> ESGMetrics:
        """Phase 4: Query metrics from data lake.

        Returns:
            ESGMetrics retrieved from DuckDB query
        """
```

### Key Methods

1. **run_pipeline(company_cik, fiscal_year)**
   - Main entry point
   - Sequentially calls _phase2_crawl → _phase3_extract → _phase4_write → _phase4_query
   - Error handling: If any phase fails, log and return PipelineResult(success=False)
   - No cascade failures (errors don't propagate)

2. **_phase2_crawl(company_cik, fiscal_year)**
   - Call `MultiSourceCrawlerV2.crawl_company(cik, fiscal_year)`
   - Return: `{"content": "...", "source": "SEC_EDGAR", "timestamp": "...", "sha256": "..."}`

3. **_phase3_extract(report)**
   - Call `ExtractionRouter.extract(report)`
   - Return: ESGMetrics instance

4. **_phase4_write(metrics, filename)**
   - Call `ParquetWriter.write_metrics(metrics, filename)`
   - Return: Path to Parquet file

5. **_phase4_query(company_name)**
   - Call `DuckDBReader.get_latest_metrics(company_name, filename)`
   - Return: ESGMetrics from query

---

## Critical Path File 2: IntegrationValidator

**File**: `apps/integration_validator.py`
**Lines**: ~100
**Purpose**: Validate data integrity, completeness, and correctness across phases

### Class Definition

```python
class IntegrationValidator:
    """Validates end-to-end pipeline output."""

    def __init__(self):
        """Initialize validator."""
        self.errors = []
        self.warnings = []

    def validate_sha256(
        self,
        data: Any,
        expected_hash: str,
        phase_name: str
    ) -> bool:
        """Validate SHA256 hash at phase boundary.

        Args:
            data: Data object (dict, bytes, etc.)
            expected_hash: Expected SHA256 hash string
            phase_name: Phase name for logging

        Returns:
            True if hash matches, False otherwise
        """

    def validate_completeness(
        self,
        metrics: ESGMetrics,
        min_completion: float = 0.95
    ) -> bool:
        """Validate ≥95% of fields are populated.

        Args:
            metrics: ESGMetrics instance
            min_completion: Minimum completion percentage (default 0.95)

        Returns:
            True if ≥min_completion%, False otherwise
        """

    def validate_ground_truth(
        self,
        metrics: ESGMetrics,
        ground_truth: dict,
        tolerance: float = 0.01
    ) -> bool:
        """Validate metrics match ground truth (±1% tolerance).

        Args:
            metrics: Extracted ESGMetrics
            ground_truth: Dict with expected values
            tolerance: Tolerance as decimal (0.01 = ±1%)

        Returns:
            True if all metrics within tolerance, False otherwise
        """

    def validate_performance(
        self,
        start_time: float,
        end_time: float,
        max_latency: float = 60.0
    ) -> bool:
        """Validate latency is <60 seconds.

        Args:
            start_time: Pipeline start timestamp
            end_time: Pipeline end timestamp
            max_latency: Maximum allowed latency (seconds)

        Returns:
            True if latency < max_latency, False otherwise
        """
```

### Key Methods

1. **validate_sha256(data, expected_hash, phase_name)**
   - Compute SHA256 of data
   - Compare with expected_hash
   - Log error if mismatch

2. **validate_completeness(metrics, min_completion=0.95)**
   - Count non-null fields in metrics
   - Calculate completion % = (total - null) / total
   - Return True if ≥95%

3. **validate_ground_truth(metrics, ground_truth, tolerance=0.01)**
   - For each metric in ground_truth:
     - Compute relative error = |extracted - expected| / expected
     - Check if error ≤ tolerance (1%)
   - Return True if all metrics pass

4. **validate_performance(start_time, end_time, max_latency=60.0)**
   - Calculate latency = end_time - start_time
   - Return True if latency < max_latency

---

## Data Flow & Phase Boundaries

### Phase 2 → Phase 3 Boundary
**Data Format**: `CompanyReport` (from Phase 2)
- Fields: company_name, cik, fiscal_year, local_path, content, sha256
- Validation: SHA256 of local_path matches report.sha256

### Phase 3 → Phase 4 Boundary
**Data Format**: `ESGMetrics` (Pydantic model from Phase 3)
- Fields: company_name, cik, fiscal_year, assets, liabilities, net_income, etc.
- Validation: All required fields present, no data type mismatches

### Phase 4 Write → Query Boundary
**Data Format**: Parquet file (bytes)
- Storage: `data_lake/<company_name>_<cik>_<fiscal_year>.parquet`
- Validation: Parquet file is readable, schema matches ESG_METRICS_PARQUET_SCHEMA

---

## Error Handling Strategy

### Fail-Fast on Critical Errors
**Critical errors** (stop pipeline):
- Phase 2: Crawler fails to download report (company not found, API error)
- Phase 3: Extractor fails to parse report (invalid format)
- Phase 4 Write: Parquet write fails (disk full)
- Phase 4 Query: DuckDB query fails (schema mismatch)

**Action**: Log error, return PipelineResult(success=False, error="..."), STOP

### Log-and-Continue on Warnings
**Warnings** (log but continue):
- Phase 3: Some metrics are null (acceptable, depends on company)
- Phase 4 Query: Completeness <95% but ≥80% (log warning, continue validation)

**Action**: Log warning, continue to next phase

---

## Logging & Metrics Collection

### Log File Structure
**Path**: `qa/pipeline_<cik>_<year>.log`

**Format**:
```
2025-10-24 16:15:30 [INFO] Pipeline start: CIK=0000789019, Year=2024
2025-10-24 16:15:35 [INFO] Phase 2 complete: crawled in 5s
2025-10-24 16:15:40 [INFO] Phase 3 complete: extracted in 5s, 13 metrics
2025-10-24 16:15:45 [INFO] Phase 4 Write complete: written in 5s
2025-10-24 16:15:50 [INFO] Phase 4 Query complete: queried in 5s
2025-10-24 16:15:50 [INFO] Pipeline total: 20s
2025-10-24 16:15:50 [INFO] Validation: completeness=100%, match=100%
```

### Metrics Captured
- `phase2_latency`: Crawl time (seconds)
- `phase3_latency`: Extract time (seconds)
- `phase4_write_latency`: Write time (seconds)
- `phase4_query_latency`: Query time (seconds)
- `total_latency`: Total pipeline time (seconds)
- `metrics_count`: Number of metrics extracted
- `null_fields_count`: Number of null fields
- `completeness_pct`: (metrics - nulls) / metrics * 100

---

## Testing Strategy

### Unit Tests (Before Integration Tests)
- Test each phase in isolation with mock data
- Test error handling (exception raised, caught, logged)
- Test logging output

### Integration Tests
- Test Phase 2→3 handoff with real crawler output
- Test Phase 3→4 handoff with real extractor output
- Test Phase 4 write→query with real Parquet file
- **Full pipeline tests**: Microsoft & Tesla end-to-end

### Test Fixtures
- Real crawler output for Microsoft (cached from Phase 2)
- Real extractor output for Microsoft (cached from Phase 3)
- Ground truth for Microsoft (manually verified from SEC)
- Same for Tesla

---

## Success Metrics Recap

| Metric | Target | Validation |
|--------|--------|-----------|
| Companies processed | ≥2 | Microsoft, Tesla both success |
| SHA256 validation | 100% | Zero mismatches at boundaries |
| Field completeness | ≥95% | 13+ of 14 fields populated |
| Ground truth match | ±1% | assets, income within tolerance |
| Pipeline latency | <60s | Total time from crawl to query |

---

**Prepared By**: Scientific Coding Agent v13.8-MEA
**Status**: Architecture & Design Complete
**Next**: Create evidence.json
