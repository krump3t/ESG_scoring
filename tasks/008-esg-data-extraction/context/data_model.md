# ESG Evidence Storage Data Model

**Version:** 1.0
**Date:** 2025-10-23
**Status:** Draft for Review
**Owner:** Task 008 - ESG Data Extraction

---

## 1. Overview

This document defines the comprehensive data modeling strategy for ESG evidence storage, retrieval, and scoring. The model is designed to:

1. **Fulfill ALL ESG Rubric v3.0 requirements** (7 themes × 5 stages)
2. **Optimize for ESG maturity assessment** while remaining extensible to other sustainability domains
3. **Support explainability** via citation-linked evidence with freshness tracking
4. **Enable deduplication** with recency preference
5. **Use DuckDB** for local analytics and query performance

---

## 2. Architecture: Bronze → Silver → Gold

### 2.1 Layer Responsibilities

| Layer | Purpose | Mutability | Retention |
|-------|---------|------------|-----------|
| **Bronze** | Raw evidence extractions as ingested | Append-only | 7 years |
| **Silver** | Deduplicated, normalized evidence | Upserts via MERGE | 7 years |
| **Gold** | Aggregated maturity scores with citations | Snapshot-based | Indefinite |

### 2.2 Data Flow

```
SEC Filing HTML
  ↓ (Evidence Extractor)
Bronze: esg_evidence_raw
  ↓ (Deduplication + Normalization)
Silver: esg_evidence_normalized
  ↓ (Rubric Scorer)
Gold: esg_maturity_scores
```

---

## 3. Bronze Layer: `esg_evidence_raw`

### 3.1 Schema Definition

```sql
CREATE TABLE esg_evidence_raw (
    -- Primary Evidence Fields (per Rubric v3.0 lines 116-122)
    evidence_id         VARCHAR PRIMARY KEY,    -- UUID v4
    org_id              VARCHAR NOT NULL,        -- CIK or ticker
    year                INTEGER NOT NULL,        -- Fiscal year
    theme               VARCHAR NOT NULL,        -- {TSP|OSP|DM|GHG|RD|EI|RMM}
    stage_indicator     INTEGER NOT NULL,        -- 0-4
    doc_id              VARCHAR NOT NULL,        -- SEC accession number
    page_no             INTEGER NOT NULL,        -- Approximate page from char offset
    span_start          INTEGER NOT NULL,        -- Character offset in document
    span_end            INTEGER NOT NULL,        -- Character offset in document
    extract_30w         VARCHAR NOT NULL,        -- 30-word context window
    hash_sha256         VARCHAR NOT NULL,        -- For deduplication (16 chars)
    snapshot_id         VARCHAR NOT NULL,        -- Extraction run ID

    -- Scoring & Traceability Fields
    confidence          DOUBLE NOT NULL,         -- 0.0 - 1.0
    evidence_type       VARCHAR NOT NULL,        -- e.g., "sbti_validation", "scope3_disclosure"
    extraction_timestamp TIMESTAMP NOT NULL,     -- When evidence was extracted (for freshness)

    -- Document Manifest (for AstraDB pointer per rubric)
    doc_manifest_uri    VARCHAR,                 -- Pointer to raw doc in AstraDB/S3
    filing_url          VARCHAR,                 -- Original SEC EDGAR URL

    -- Schema Evolution
    schema_version      INTEGER NOT NULL DEFAULT 1,
    metadata            JSON,                    -- Extensible key-value pairs

    -- Audit Trail
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ingestion_id        VARCHAR NOT NULL         -- Batch/run identifier
)
PARTITION BY (org_id, year, theme);
```

### 3.2 Constraints & Validation

```sql
-- Theme validation
CHECK (theme IN ('TSP', 'OSP', 'DM', 'GHG', 'RD', 'EI', 'RMM'))

-- Stage bounds
CHECK (stage_indicator BETWEEN 0 AND 4)

-- Confidence bounds
CHECK (confidence BETWEEN 0.0 AND 1.0)

-- Year sanity
CHECK (year BETWEEN 1900 AND 2100)

-- Span ordering
CHECK (span_end > span_start)

-- Page number
CHECK (page_no >= 1)
```

### 3.3 Indexes

```sql
-- Primary lookup patterns
CREATE INDEX idx_org_year_theme ON esg_evidence_raw(org_id, year, theme);

-- Deduplication lookups
CREATE INDEX idx_hash_org_year ON esg_evidence_raw(hash_sha256, org_id, year);

-- Snapshot queries
CREATE INDEX idx_snapshot ON esg_evidence_raw(snapshot_id);

-- Freshness queries
CREATE INDEX idx_extraction_ts ON esg_evidence_raw(extraction_timestamp DESC);
```

### 3.4 Partitioning Strategy

- **Hive-style partitioning**: `/org_id=MSFT/year=2023/theme=GHG/`
- **Benefits**:
  - Partition pruning for single-company queries
  - Parallel processing by theme
  - Easy archival of old years
- **DuckDB**: Use `PARTITION BY (org_id, year, theme)` in table definition

---

## 4. Silver Layer: `esg_evidence_normalized`

### 4.1 Schema Definition

```sql
CREATE TABLE esg_evidence_normalized (
    -- Same fields as bronze layer
    evidence_id         VARCHAR PRIMARY KEY,
    org_id              VARCHAR NOT NULL,
    year                INTEGER NOT NULL,
    theme               VARCHAR NOT NULL,
    stage_indicator     INTEGER NOT NULL,
    doc_id              VARCHAR NOT NULL,
    page_no             INTEGER NOT NULL,
    span_start          INTEGER NOT NULL,
    span_end            INTEGER NOT NULL,
    extract_30w         VARCHAR NOT NULL,
    hash_sha256         VARCHAR NOT NULL,
    snapshot_id         VARCHAR NOT NULL,
    confidence          DOUBLE NOT NULL,
    evidence_type       VARCHAR NOT NULL,
    extraction_timestamp TIMESTAMP NOT NULL,
    doc_manifest_uri    VARCHAR,
    filing_url          VARCHAR,
    schema_version      INTEGER NOT NULL DEFAULT 1,
    metadata            JSON,

    -- Silver-Specific Fields
    is_most_recent      BOOLEAN NOT NULL DEFAULT TRUE,   -- For deduplication
    superseded_by       VARCHAR,                          -- Points to newer evidence_id
    relevance_score     DOUBLE,                           -- For top-10 ranking
    freshness_penalty   DOUBLE NOT NULL DEFAULT 0.0,     -- Calculated from 24-month rule
    adjusted_confidence DOUBLE NOT NULL,                  -- confidence - freshness_penalty

    -- Audit Trail
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ingestion_id        VARCHAR NOT NULL
)
PARTITION BY (org_id, year, theme);
```

### 4.2 Deduplication Logic

**Strategy**: Hash-based deduplication with confidence-first tie-breaking

```sql
-- MERGE logic (idempotent upserts)
MERGE INTO esg_evidence_normalized AS target
USING (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY hash_sha256, org_id, year
            ORDER BY confidence DESC, extraction_timestamp DESC
        ) AS rn
    FROM esg_evidence_raw
    WHERE ingestion_id = ?
) AS source
ON target.hash_sha256 = source.hash_sha256
   AND target.org_id = source.org_id
   AND target.year = source.year

WHEN MATCHED AND source.rn = 1 THEN
    UPDATE SET
        -- Mark old record as superseded
        is_most_recent = FALSE,
        superseded_by = source.evidence_id,
        updated_at = CURRENT_TIMESTAMP

WHEN NOT MATCHED AND source.rn = 1 THEN
    INSERT (evidence_id, org_id, year, ..., is_most_recent)
    VALUES (source.evidence_id, source.org_id, source.year, ..., TRUE);
```

**Deduplication Rules**:
1. **Same hash + org + year** = duplicate
2. **Keep highest confidence** first, then most recent by `extraction_timestamp`
3. **Mark superseded** records with `is_most_recent = FALSE`
4. **Retain history** for audit trails (don't delete old records)

### 4.3 Freshness Calculation

**Rubric Requirement**: Evidence >24 months old reduces confidence by 0.1

**Enhancement**: Graduated penalties for more nuanced scoring

```sql
-- Graduated freshness penalty calculation
UPDATE esg_evidence_normalized
SET
    freshness_penalty = CASE
        WHEN DATEDIFF('month', extraction_timestamp, CURRENT_TIMESTAMP) > 48
        THEN 0.3
        WHEN DATEDIFF('month', extraction_timestamp, CURRENT_TIMESTAMP) > 36
        THEN 0.2
        WHEN DATEDIFF('month', extraction_timestamp, CURRENT_TIMESTAMP) > 24
        THEN 0.1
        ELSE 0.0
    END,
    adjusted_confidence = GREATEST(0.0, confidence - freshness_penalty);
```

**Penalty Schedule**:
- 0-24 months: No penalty (fresh evidence)
- 25-36 months: -0.1 confidence
- 37-48 months: -0.2 confidence
- >48 months: -0.3 confidence (stale evidence)

**Applied During**:
- Silver layer normalization (calculated once per record)
- Query time (recalculated for dynamic freshness)

---

## 5. Gold Layer: `esg_maturity_scores`

### 5.1 Schema Definition

```sql
CREATE TABLE esg_maturity_scores (
    -- Composite Key
    score_id            VARCHAR PRIMARY KEY,     -- UUID v4
    org_id              VARCHAR NOT NULL,
    year                INTEGER NOT NULL,
    snapshot_id         VARCHAR NOT NULL,        -- Links to evidence batch

    -- Maturity Scores (per Rubric v3.0)
    tsp_score           DOUBLE,                  -- Target Setting Process (0-4)
    osp_score           DOUBLE,                  -- Organizational Structure & Process (0-4)
    dm_score            DOUBLE,                  -- Data Management (0-4)
    ghg_score           DOUBLE,                  -- GHG Accounting (0-4)
    rd_score            DOUBLE,                  -- Reporting & Disclosure (0-4)
    ei_score            DOUBLE,                  -- Efficiency Initiatives (0-4)
    rmm_score           DOUBLE,                  -- Risk Management & Materiality (0-4)

    overall_score       DOUBLE,                  -- Average of 7 themes (0-4)
    maturity_grade      VARCHAR,                 -- {Nascent|Emerging|Established|Advanced|Leading}

    -- Confidence & Freshness
    avg_confidence      DOUBLE,                  -- Average adjusted_confidence
    evidence_count      INTEGER,                 -- Total evidence items used
    oldest_evidence_date TIMESTAMP,              -- For freshness tracking

    -- Evidence Linkage (per Rubric lines 116-122)
    evidence_ids        JSON,                    -- Array of evidence_id refs
    doc_manifest_uri    VARCHAR,                 -- AstraDB pointer to document manifest

    -- Top-10 Excerpts (for Explainability Agent)
    top_excerpts        JSON,                    -- Ranked by relevance × recency

    -- Audit Trail
    scored_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    scorer_version      VARCHAR NOT NULL,        -- e.g., "rubric_v3.0"
    metadata            JSON
)
PARTITION BY (org_id, year);
```

### 5.2 Maturity Grade Calculation

**Per Rubric v3.0**:

```sql
-- Overall score = average of 7 theme scores
overall_score = (tsp_score + osp_score + dm_score + ghg_score + rd_score + ei_score + rmm_score) / 7.0

-- Grade mapping
maturity_grade = CASE
    WHEN overall_score < 1.0  THEN 'Nascent'
    WHEN overall_score < 2.0  THEN 'Emerging'
    WHEN overall_score < 3.0  THEN 'Established'
    WHEN overall_score < 3.6  THEN 'Advanced'
    ELSE 'Leading'
END
```

### 5.3 Top-10 Excerpts Ranking

**Rubric Requirement**: "Explainability Agent ranks top‑10 excerpts by relevance × recency"

```sql
-- Example top_excerpts JSON structure
{
  "excerpts": [
    {
      "rank": 1,
      "evidence_id": "ev_abc123",
      "theme": "GHG",
      "extract_30w": "...we have set science-based targets aligned with SBTi...",
      "relevance_score": 0.95,
      "recency_score": 1.0,
      "combined_score": 0.95,
      "page_no": 42,
      "doc_id": "0000891020-23-000077"
    },
    ...
  ]
}
```

**Ranking Logic**:
```python
# Relevance: How well evidence matches stage criteria (matcher-specific)
# Recency: 1.0 if <24 months, 0.9 if 24-36 months, 0.8 if >36 months

combined_score = relevance_score * recency_score
top_10 = sorted(evidence, key=lambda e: e.combined_score, reverse=True)[:10]
```

---

## 6. Theme Overlap Rules

### 6.1 Policy

**User Requirement**: "Theme overlap with same evidence should only occur when it is truly applicable to different and relevant to those themes."

**Implementation**:
1. **Evidence is theme-specific** by default (single theme per evidence record)
2. **Cross-theme applicability** controlled via `evidence_type` classification
3. **Explicit overlap matrix** defines allowed cross-theme evidence

### 6.2 Cross-Theme Applicability Matrix

| Evidence Type | Primary Theme | Allowed Overlaps | Justification |
|---------------|---------------|------------------|---------------|
| `sbti_validation` | TSP | GHG, RD | SBTi validates both targets (TSP) and GHG accounting (GHG) + reporting (RD) |
| `scope3_disclosure` | GHG | RD, RMM | Scope 3 is GHG metric but also disclosure (RD) and supply chain risk (RMM) |
| `tcfd_alignment` | RD | RMM | TCFD is reporting framework (RD) covering risk (RMM) |
| `assurance_statement` | RD | GHG, OSP | Assurance covers reporting (RD), GHG accuracy (GHG), and governance (OSP) |
| `esg_committee` | OSP | RMM | Governance structure (OSP) managing ESG risks (RMM) |
| `carbon_pricing` | TSP | EI, RMM | Internal carbon price supports targets (TSP), efficiency (EI), risk mgmt (RMM) |

### 6.3 Validation Logic

```python
# Pseudo-code for theme overlap validation
OVERLAP_MATRIX = {
    "sbti_validation": ["TSP", "GHG", "RD"],
    "scope3_disclosure": ["GHG", "RD", "RMM"],
    # ... rest of matrix
}

def validate_evidence_theme(evidence_type: str, theme: str) -> bool:
    """Ensure theme is allowed for this evidence type."""
    allowed_themes = OVERLAP_MATRIX.get(evidence_type, [theme])
    return theme in allowed_themes
```

**Storage Approach** (Approved):
- **Duplicate evidence records** (one per theme, same hash_sha256)
- **Rationale**: Query simplicity and partition pruning performance
- **Trade-off**: Slight storage overhead (acceptable) vs. faster queries (significant benefit)
- **Implementation**: Extract evidence once, replicate with different `theme` values based on OVERLAP_MATRIX

---

## 7. DuckDB Implementation

**Approved Approach**: Parquet files + DuckDB views (local data lakehouse pattern)

### 7.1 Parquet Storage with Hive Partitioning

```python
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import List
from agents.parser.models import Evidence

# Define Parquet schema matching rubric requirements
EVIDENCE_SCHEMA = pa.schema([
    ('evidence_id', pa.string()),
    ('org_id', pa.string()),
    ('year', pa.int32()),
    ('theme', pa.string()),
    ('stage_indicator', pa.int32()),
    ('doc_id', pa.string()),
    ('page_no', pa.int32()),
    ('span_start', pa.int32()),
    ('span_end', pa.int32()),
    ('extract_30w', pa.string()),
    ('hash_sha256', pa.string()),
    ('snapshot_id', pa.string()),
    ('confidence', pa.float64()),
    ('evidence_type', pa.string()),
    ('extraction_timestamp', pa.timestamp('us')),
    ('doc_manifest_uri', pa.string()),
    ('filing_url', pa.string()),
    ('schema_version', pa.int32()),
    ('created_at', pa.timestamp('us')),
    ('ingestion_id', pa.string())
])

def write_bronze_evidence(
    evidence_list: List[Evidence],
    base_path: Path,
    ingestion_id: str
) -> None:
    """Write evidence to Parquet with Hive partitioning."""
    # Convert Evidence objects to PyArrow table
    # Partition by org_id/year/theme
    # Write to: data/bronze/org_id=MSFT/year=2023/theme=GHG/part-0.parquet
    ...
```

### 7.2 DuckDB Views Over Parquet

```python
import duckdb
from pathlib import Path

def create_duckdb_views(db_path: Path, parquet_base_path: Path) -> None:
    """Create DuckDB views over Parquet files."""
    con = duckdb.connect(str(db_path))

    # Bronze view
    con.execute(f"""
        CREATE OR REPLACE VIEW bronze_evidence AS
        SELECT * FROM read_parquet('{parquet_base_path}/bronze/**/*.parquet',
                                     hive_partitioning=true)
    """)

    # Silver view (with constraints)
    con.execute(f"""
        CREATE OR REPLACE VIEW silver_evidence AS
        SELECT *
        FROM read_parquet('{parquet_base_path}/silver/**/*.parquet',
                           hive_partitioning=true)
        WHERE theme IN ('TSP', 'OSP', 'DM', 'GHG', 'RD', 'EI', 'RMM')
          AND stage_indicator BETWEEN 0 AND 4
          AND confidence BETWEEN 0.0 AND 1.0
    """)

    # Create indexes for query performance
    con.execute("CREATE INDEX IF NOT EXISTS idx_org_year_theme ON silver_evidence(org_id, year, theme)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_hash ON silver_evidence(hash_sha256)")

    con.close()
```

**Benefits of Parquet + DuckDB Approach**:
- ✅ **Portability**: Parquet files readable by any tool (Python, Spark, Power BI)
- ✅ **Performance**: DuckDB's vectorized query engine optimized for Parquet
- ✅ **Storage efficiency**: Columnar compression (3-10x smaller than row-based)
- ✅ **Partition pruning**: Skip irrelevant partitions (org_id/year/theme)
- ✅ **No lock-in**: Avoid monolithic .duckdb file dependency

### 7.3 Query Patterns

#### Q1: Get All Evidence for Company/Year/Theme

```sql
SELECT
    evidence_id,
    page_no,
    extract_30w,
    evidence_type,
    stage_indicator,
    confidence,
    extraction_timestamp
FROM esg_evidence_normalized
WHERE org_id = 'MSFT'
  AND year = 2023
  AND theme = 'GHG'
  AND is_most_recent = TRUE
ORDER BY adjusted_confidence DESC;
```

#### Q2: Get Maturity Score with Evidence Citations

```sql
SELECT
    s.org_id,
    s.year,
    s.ghg_score,
    s.overall_score,
    s.maturity_grade,
    s.evidence_count,
    s.top_excerpts,
    e.extract_30w,
    e.page_no,
    e.doc_id
FROM esg_maturity_scores s
CROSS JOIN LATERAL UNNEST(s.evidence_ids) AS ev_id
JOIN esg_evidence_normalized e ON e.evidence_id = ev_id
WHERE s.org_id = 'MSFT'
  AND s.year = 2023;
```

#### Q3: Compare Companies Across Themes

```sql
SELECT
    org_id,
    year,
    ghg_score,
    rd_score,
    ei_score,
    overall_score,
    maturity_grade,
    evidence_count
FROM esg_maturity_scores
WHERE year = 2023
  AND org_id IN ('MSFT', 'AAPL', 'TSLA', 'XOM', 'TGT')
ORDER BY overall_score DESC;
```

#### Q4: Top-10 Excerpts by Relevance × Recency (Explainability)

```sql
-- Already stored in gold.esg_maturity_scores.top_excerpts JSON
-- Retrieve with:
SELECT
    org_id,
    year,
    theme,
    top_excerpts->>'excerpts' AS ranked_excerpts
FROM esg_maturity_scores
WHERE org_id = 'MSFT' AND year = 2023;
```

#### Q5: Freshness-Adjusted Confidence Scores

```sql
SELECT
    org_id,
    year,
    theme,
    evidence_type,
    confidence AS original_confidence,
    freshness_penalty,
    adjusted_confidence,
    DATEDIFF('month', extraction_timestamp, CURRENT_TIMESTAMP) AS age_months
FROM esg_evidence_normalized
WHERE org_id = 'MSFT'
  AND year = 2023
  AND is_most_recent = TRUE
ORDER BY adjusted_confidence DESC;
```

---

## 8. Schema Evolution Strategy

### 8.1 Extensibility for New Themes

**Scenario**: Add Theme #8: Water Management (WM)

**Changes Required**:
1. Update `CHECK (theme IN (...))` constraint to include `'WM'`
2. Add `wm_score DOUBLE` column to `esg_maturity_scores`
3. Update overall_score calculation: `/ 8.0` instead of `/ 7.0`
4. Add WM matcher to `agents/parser/matchers/wm_matcher.py`
5. Update cross-theme overlap matrix if applicable

**Migration**:
```sql
-- Add new theme to constraint (DuckDB doesn't support ALTER CHECK, need to recreate)
-- Workaround: Use application-level validation or recreate table

-- Add new score column
ALTER TABLE esg_maturity_scores ADD COLUMN wm_score DOUBLE DEFAULT NULL;

-- Backfill: Re-score existing records if WM evidence exists
UPDATE esg_maturity_scores
SET wm_score = (SELECT AVG(stage_indicator) FROM esg_evidence_normalized WHERE theme = 'WM' AND org_id = esg_maturity_scores.org_id AND year = esg_maturity_scores.year);
```

### 8.2 Extensibility for New Evidence Fields

**Scenario**: Add `llm_extracted BOOLEAN` field to track LLM vs. regex-based extraction

**Changes Required**:
1. Add column to bronze/silver tables
2. Increment `schema_version` to 2
3. Update Evidence Python dataclass
4. Backfill existing records with `llm_extracted = FALSE`

**Migration**:
```sql
-- Add new field
ALTER TABLE esg_evidence_raw ADD COLUMN llm_extracted BOOLEAN DEFAULT FALSE;
ALTER TABLE esg_evidence_normalized ADD COLUMN llm_extracted BOOLEAN DEFAULT FALSE;

-- Update schema version for new records
-- (existing records remain at schema_version = 1)
```

**Query Compatibility**:
```python
# Handle multi-version schemas in queries
def get_evidence(org_id: str, year: int) -> List[Evidence]:
    """Retrieve evidence, handling schema version differences."""
    con = duckdb.connect(DB_PATH)

    result = con.execute("""
        SELECT
            *,
            COALESCE(llm_extracted, FALSE) AS llm_extracted_safe
        FROM esg_evidence_normalized
        WHERE org_id = ? AND year = ?
    """, [org_id, year]).fetchdf()

    return [Evidence(**row) for row in result.to_dict('records')]
```

### 8.3 Migration from Vertical Slice (GHG) to Horizontal Breadth (All 7)

**Current State**: GHG matcher only
**Target State**: All 7 matchers (TSP, OSP, DM, GHG, RD, EI, RMM)

**Migration Path**:
1. **Phase 1 (Current)**: GHG evidence only
   - Bronze/silver tables contain only `theme = 'GHG'` records
   - Gold scores have only `ghg_score` populated (others NULL)

2. **Phase 2 (Horizontal Expansion)**:
   - Add 6 new matchers
   - Run batch extraction on same 5 companies
   - Insert new evidence with `theme IN ('TSP', 'OSP', 'DM', 'RD', 'EI', 'RMM')`
   - Re-score to populate all 7 theme scores

3. **Phase 3 (Scale to 25 Companies)**:
   - Same schema, just more `org_id` values
   - Partition pruning ensures query performance

**No Schema Changes Required** - existing schema already supports all 7 themes!

---

## 9. Data Quality & Validation

### 9.1 Validation Rules

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class EvidenceValidationResult:
    """Result of evidence validation checks."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

def validate_evidence(evidence: Evidence) -> EvidenceValidationResult:
    """Validate evidence against data model constraints."""
    errors = []
    warnings = []

    # Theme validation
    VALID_THEMES = {'TSP', 'OSP', 'DM', 'GHG', 'RD', 'EI', 'RMM'}
    if evidence.theme not in VALID_THEMES:
        errors.append(f"Invalid theme: {evidence.theme}")

    # Stage validation
    if not (0 <= evidence.stage_indicator <= 4):
        errors.append(f"Stage must be 0-4, got {evidence.stage_indicator}")

    # Confidence validation
    if not (0.0 <= evidence.confidence <= 1.0):
        errors.append(f"Confidence must be 0.0-1.0, got {evidence.confidence}")

    # Year sanity check
    if not (1900 <= evidence.year <= 2100):
        errors.append(f"Year out of range: {evidence.year}")

    # Span ordering
    if evidence.span_end <= evidence.span_start:
        errors.append(f"span_end must be > span_start")

    # Context length warning
    if len(evidence.extract_30w.split()) < 20:
        warnings.append(f"Context has fewer than 20 words (expected ~30)")

    return EvidenceValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )
```

### 9.2 Monitoring Queries

```sql
-- Data Quality Dashboard

-- 1. Evidence count by theme
SELECT theme, COUNT(*) as evidence_count
FROM esg_evidence_normalized
WHERE is_most_recent = TRUE
GROUP BY theme;

-- 2. Average confidence by theme
SELECT theme, AVG(adjusted_confidence) as avg_confidence
FROM esg_evidence_normalized
WHERE is_most_recent = TRUE
GROUP BY theme;

-- 3. Freshness distribution
SELECT
    CASE
        WHEN DATEDIFF('month', extraction_timestamp, CURRENT_TIMESTAMP) < 12 THEN '<1 year'
        WHEN DATEDIFF('month', extraction_timestamp, CURRENT_TIMESTAMP) < 24 THEN '1-2 years'
        ELSE '>2 years'
    END AS age_bucket,
    COUNT(*) as evidence_count
FROM esg_evidence_normalized
WHERE is_most_recent = TRUE
GROUP BY age_bucket;

-- 4. Duplicate detection (should be empty if deduplication works)
SELECT hash_sha256, org_id, year, COUNT(*) as dup_count
FROM esg_evidence_normalized
WHERE is_most_recent = TRUE
GROUP BY hash_sha256, org_id, year
HAVING COUNT(*) > 1;

-- 5. Stage distribution by theme
SELECT theme, stage_indicator, COUNT(*) as count
FROM esg_evidence_normalized
WHERE is_most_recent = TRUE
GROUP BY theme, stage_indicator
ORDER BY theme, stage_indicator;
```

---

## 10. Implementation Checklist

### 10.1 Phase 1: Vertical Slice (GHG Only)

- [ ] Create DuckDB database file (`data/esg_evidence.duckdb`)
- [ ] Implement bronze table creation (`agents/storage/bronze_writer.py`)
- [ ] Implement evidence batch insertion
- [ ] Test with 5 companies × GHG matcher
- [ ] Validate deduplication logic
- [ ] Implement silver layer normalization
- [ ] Implement gold layer scoring (GHG only)
- [ ] Create Q&A validation queries
- [ ] Measure accuracy (target: ≥80%)

### 10.2 Phase 2: Horizontal Breadth (All 7 Themes)

- [ ] Implement remaining 6 matchers (TSP, OSP, DM, RD, EI, RMM)
- [ ] Update cross-theme overlap matrix
- [ ] Run batch extraction on 5 companies with all matchers
- [ ] Re-score with all 7 theme scores
- [ ] Validate overall_score and maturity_grade calculations
- [ ] Implement top-10 excerpt ranking
- [ ] Test freshness penalty logic

### 10.3 Phase 3: Scale to 25 Companies

- [ ] Expand to 25 companies (per Task 008 plan)
- [ ] Monitor query performance (partition pruning)
- [ ] Validate data quality metrics across larger dataset
- [ ] Document query patterns and performance benchmarks

---

## 11. References

1. **ESG Maturity Rubric v3.0** - `rubrics/esg_maturity_rubricv3.md` (lines 116-122)
2. **Evidence Model** - `agents/parser/models.py`
3. **Existing Bronze Schema** - `agents/crawler/writers/parquet_writer.py`
4. **Silver/Gold Architecture** - `tasks/003-iceberg-core-silver-gold/context/design.md`
5. **SCA v13.8 Protocol** - `.claude/full_protocol.md`

---

## 12. Approved Design Decisions

### Critical Decisions

1. **doc_manifest_uri Format**: Use S3 URIs (or equivalent object storage)
   - Format: `s3://esg-reports/org_id/year/doc_id.pdf`
   - Rationale: Object storage is cost-effective for large files; keeps database lean
   - Implementation: Generate URI at extraction time, store in evidence metadata

2. **Cross-Theme Overlap Storage**: Duplicate evidence records (Option A)
   - Approach: One record per theme, same hash_sha256
   - Rationale: Query simplicity and partition pruning performance
   - Trade-off: Slight storage overhead vs. significant query performance gain

3. **Relevance Scoring**: Phased approach
   - Phase 1 (Current): Matcher-specific heuristics (e.g., "SBTi" = 0.95 for TSP)
   - Phase 2 (Future): Embedding-based semantic similarity
   - Rationale: Fast implementation now, evolution path for better accuracy

4. **Storage Format**: Parquet files + DuckDB views (Option B)
   - Bronze/Silver: Parquet files with Hive partitioning
   - DuckDB: SQL views over Parquet for query layer
   - Rationale: Portability (any tool can read Parquet) + DuckDB query speed

### Quality Improvements

5. **Freshness Penalties**: Graduated decay schedule
   - >24 months: -0.1 confidence
   - >36 months: -0.2 confidence
   - >48 months: -0.3 confidence
   - Rationale: More nuanced model than hard 24-month cutoff

6. **Deduplication Tie-Breaking**: Confidence-first ordering
   - Sort by: `confidence DESC, extraction_timestamp DESC`
   - Rationale: Keep the highest-quality extraction, use recency as final tie-breaker

7. **Schema Migrations**: Enforced (schema-on-write)
   - Policy: All records updated to latest schema during migrations
   - Rationale: Clean, consistent database; simple and fast queries
   - Trade-off: One-time migration cost vs. long-term query simplicity

---

**Status**: Approved. Ready for implementation following SCA v13.8 protocol.
