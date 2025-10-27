"""
Script to create context files for all migration tasks
"""
import json
from pathlib import Path

TASKS_DIR = Path(r"C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine\tasks")

# Task 003: Iceberg Core
task_003 = TASKS_DIR / "003-iceberg-core-silver-gold" / "context"
(task_003 / "design.md").write_text("""# Design: Iceberg Silver/Gold Layers

## Silver Layer: silver.esg_normalized
- Deduplicated, normalized ESG findings
- MERGE upserts based on (org_id, finding_hash)
- Hidden partitioning on org_id, year, theme

## Gold Layer: gold.esg_scores
- Maturity scores with confidence
- Linked to AstraDB evidence manifests
- Snapshot IDs for reproducibility

## Agents:
- Normalizer: Taxonomy mapping, framework detection
- Scoring: watsonx.ai calls with improved confidence prompts
""")

(task_003 / "evidence.json").write_text(json.dumps({
    "sources": [
        {"id": "P1-001", "title": "Iceberg MERGE Operations", "url": "https://iceberg.apache.org/docs/latest/spark-writes/", "priority": "P1", "synthesis": "MERGE enables upserts with ACID guarantees"},
        {"id": "P1-002", "title": "IBM watsonx.ai API", "url": "https://ibm.github.io/watsonx-ai-python-sdk", "priority": "P1", "synthesis": "Python SDK for LLM inference with parameter control"}
    ]
}, indent=2))

(task_003 / "data_sources.json").write_text(json.dumps({
    "sources": [
        {"name": "silver_normalized", "type": "iceberg", "format": "parquet", "sha256": "dynamic", "pii_flag": False, "provenance": "transformed", "retention_days": 90},
        {"name": "gold_scores", "type": "iceberg", "format": "parquet", "sha256": "dynamic", "pii_flag": False, "provenance": "scored", "retention_days": 365}
    ]
}, indent=2))

(task_003 / "cp_paths.json").write_text(json.dumps({
    "critical_paths": ["agents/normalizer/*.py", "agents/scoring/*.py", "iceberg/tables/*.py"],
    "coverage_requirements": {"line": 0.95, "branch": 0.95}
}, indent=2))

(task_003 / "adr.md").write_text("""# ADR-001: MERGE for Upserts
**Status**: Accepted
**Decision**: Use Iceberg MERGE for silver layer upserts
**Rationale**: ACID guarantees, handles late-arriving data

# ADR-002: Improved Confidence Prompts
**Status**: Accepted
**Decision**: Use evidence-based confidence calculation in watsonx prompts
**Rationale**: Fixed 50% confidence issue, now varies 20-90%
""")

(task_003 / "assumptions.md").write_text("""# Assumptions
- watsonx.ai API stable and responsive
- AstraDB available for evidence storage
- Iceberg catalog operational from Task 001
- Bronze data available from Task 002
""")

# Task 004: QA & Explainability
task_004 = TASKS_DIR / "004-qa-explainability-agents" / "context"
(task_004 / "hypothesis.md").write_text("""# Hypothesis: QA and Explainability Agents

## Core Hypothesis
Adding QA/Assurance and Explainability agents will enable automated quality checks and transparent "why" explanations for ESG scores.

## Success Metrics
- QA gate pass rate: > 90%
- Drift detection: < 10% false positives
- Evidence retrieval: < 500ms per query
- Explanation completeness: > 95% of scores explainable

## Critical Path
- agents/qa/mcp_qa.py
- agents/explainability/mcp_explain.py
- views/report_card.sql
""")

(task_004 / "design.md").write_text("""# Design: QA and Explainability

## QA Agent Tools:
- assurance.checks: Data quality validation
- iceberg.profile: Statistical profiling
- drift.compare: Detect scoring drift

## Explainability Agent Tools:
- evidence.table: Retrieve evidence for scores
- graphrag.expand: Expand via AstraDB graph
- join.columnar: Join Iceberg + AstraDB data
""")

(task_004 / "evidence.json").write_text(json.dumps({
    "sources": [
        {"id": "P1-001", "title": "Explainable AI: Interpreting, Explaining and Visualizing Deep Learning", "priority": "P1"}
    ]
}, indent=2))

(task_004 / "data_sources.json").write_text(json.dumps({
    "sources": [{"name": "qa_reports", "type": "artifact", "sha256": "dynamic", "pii_flag": False}]
}, indent=2))

(task_004 / "cp_paths.json").write_text(json.dumps({
    "critical_paths": ["agents/qa/*.py", "agents/explainability/*.py"]
}, indent=2))

(task_004 / "adr.md").write_text("# ADR-001: Statistical Drift Detection\n**Status**: Accepted")
(task_004 / "assumptions.md").write_text("# Assumptions\n- Gold layer operational\n- AstraDB graph populated")

# Task 005: Ops & Freshness
task_005 = TASKS_DIR / "005-ops-freshness-agent" / "context"
(task_005 / "hypothesis.md").write_text("""# Hypothesis: Ops and Freshness Agent

## Success Metrics
- Stale detection: 100% recall for data > 24 months old
- MCP trigger accuracy: > 90% when quality < 0.7
- Re-ingestion throughput: > 5 companies/day
""")

(task_005 / "design.md").write_text("""# Design: Ops Agent

## Tools:
- timegate.check: Scan Iceberg snapshots for staleness
- reingest.if_stale: Trigger Crawler Agent
- coverage.report: Generate data coverage metrics
""")

(task_005 / "evidence.json").write_text(json.dumps({"sources": []}, indent=2))
(task_005 / "data_sources.json").write_text(json.dumps({"sources": []}, indent=2))
(task_005 / "cp_paths.json").write_text(json.dumps({"critical_paths": ["agents/ops/*.py"]}, indent=2))
(task_005 / "adr.md").write_text("# ADR-001: Quality-Triggered Fetching\n**Status**: Accepted")
(task_005 / "assumptions.md").write_text("# Assumptions\n- MCP report fetcher operational")

# Task 006: Cutover & Migration
task_006 = TASKS_DIR / "006-cutover-migration" / "context"
(task_006 / "hypothesis.md").write_text("""# Hypothesis: Cutover and Migration

## Success Metrics
- Dual-run match rate: > 95% score agreement
- Migration time: < 2 weeks
- Zero data loss
""")

(task_006 / "design.md").write_text("""# Design: Migration Strategy

## Approach:
1. Dual-run: Legacy + Iceberg parallel
2. QA diff reports
3. 2-week validation
4. Cutover when match rate > 95%
""")

(task_006 / "evidence.json").write_text(json.dumps({"sources": []}, indent=2))
(task_006 / "data_sources.json").write_text(json.dumps({"sources": []}, indent=2))
(task_006 / "cp_paths.json").write_text(json.dumps({"critical_paths": ["migration/*.py"]}, indent=2))
(task_006 / "adr.md").write_text("# ADR-001: Gradual Migration\n**Status**: Accepted")
(task_006 / "assumptions.md").write_text("# Assumptions\n- Can run both systems in parallel")

# Task 007: Hardening
task_007 = TASKS_DIR / "007-hardening-optimization" / "context"
(task_007 / "hypothesis.md").write_text("""# Hypothesis: Hardening and Optimization

## Success Metrics
- Query P95 latency: < 1 second
- Compaction overhead: < 10% of writes
- Storage efficiency: > 80% (vs uncompressed)
""")

(task_007 / "design.md").write_text("""# Design: Production Hardening

## Optimizations:
- Iceberg compaction policies
- ZSTD compression tuning
- Bloom filters on hot columns
- Snapshot retention (90 days + monthly)
""")

(task_007 / "evidence.json").write_text(json.dumps({"sources": []}, indent=2))
(task_007 / "data_sources.json").write_text(json.dumps({"sources": []}, indent=2))
(task_007 / "cp_paths.json").write_text(json.dumps({"critical_paths": ["optimization/*.py"]}, indent=2))
(task_007 / "adr.md").write_text("# ADR-001: ZSTD Level 3-5\n**Status**: Accepted")
(task_007 / "assumptions.md").write_text("# Assumptions\n- All previous tasks complete")

print("All task context files created successfully!")
