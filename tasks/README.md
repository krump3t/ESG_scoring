# MCP + Apache Iceberg Migration Tasks

This directory contains the protocol-compliant task structure for migrating the ESG evaluation system to a multi-agent MCP architecture with Apache Iceberg tables.

## Task Overview

All tasks follow SCA Protocol v13.7 requirements with full traceability artifacts.

### Task 001: MCP + Iceberg Infrastructure (`001-mcp-iceberg-infrastructure/`)
**Status**: Ready for Phase: context
**Goal**: Stand up local MinIO, Iceberg catalog (REST/Nessie), Trino, and MCP server foundation

**Key Deliverables**:
- docker-compose.yml for all services
- MinIO with bronze/silver/gold buckets
- Iceberg REST catalog operational
- Trino connected to Iceberg
- MCP server base with tool registration
- Health check endpoints

**Success Criteria**:
- All 14 gates passing
- Services start in < 5 seconds
- Query response < 100ms
- Memory usage < 4GB

---

### Task 002: Bronze Landing (`002-bronze-landing/`)
**Status**: Ready for Phase: context
**Goal**: Implement MCP Crawler Agent writing raw Parquet to bronze layer

**Key Deliverables**:
- MCP Crawler Agent with tools: `sustainability.fetch`, `pdf.extract`, `parquet.land`
- PDF/HTML/PPTX extraction pipelines
- Append-only Parquet writes to MinIO
- Real sustainability report fetching

**Success Criteria**:
- Extraction success rate > 95%
- Throughput > 10 docs/min
- Text extraction accuracy > 90%
- Deduplication 100% accurate

---

### Task 003: Iceberg Core - Silver & Gold (`003-iceberg-core-silver-gold/`)
**Status**: Ready for Phase: context
**Goal**: Create Iceberg tables and implement Normalizer + Scoring agents

**Key Deliverables**:
- Iceberg tables: `silver.esg_normalized`, `gold.esg_scores`, `gold.esg_evidence`
- Normalizer Agent with MERGE upserts
- Scoring Agent with improved watsonx.ai confidence prompts
- AstraDB manifest linkage with snapshot IDs

**Success Criteria**:
- MERGE performance > 1000 records/sec
- Confidence variance > 30% across quality levels
- watsonx.ai API success rate > 95%
- Time-travel queries < 2 second overhead

---

### Task 004: QA & Explainability Agents (`004-qa-explainability-agents/`)
**Status**: Ready for Phase: context
**Goal**: Add QA/Assurance and Explainability agents with semantic views

**Key Deliverables**:
- QA Agent tools: `assurance.checks`, `iceberg.profile`, `drift.compare`
- Explainability Agent tools: `evidence.table`, `graphrag.expand`, `join.columnar`
- Semantic views: `gold.v_scores_latest`, report-card views

**Success Criteria**:
- QA gate pass rate > 90%
- Drift detection < 10% false positives
- Evidence retrieval < 500ms
- Explanation completeness > 95%

---

### Task 005: Ops & Freshness Agent (`005-ops-freshness-agent/`)
**Status**: Ready for Phase: context
**Goal**: Implement Ops Agent for automated freshness and quality-triggered fetching

**Key Deliverables**:
- Ops Agent tools: `timegate.check`, `reingest.if_stale`, `coverage.report`
- Iceberg snapshot-based staleness detection
- MCP quality-triggered report fetching (from mcp_report_fetcher.py)
- Local scheduling (cron/Celery)

**Success Criteria**:
- Stale detection 100% recall for data > 24 months
- MCP trigger accuracy > 90% when quality < 0.7
- Re-ingestion throughput > 5 companies/day

---

### Task 006: Cutover & Migration (`006-cutover-migration/`)
**Status**: Ready for Phase: context
**Goal**: Migrate from legacy to new architecture with dual-run validation

**Key Deliverables**:
- Dual-run implementation (legacy + Iceberg parallel)
- QA diff reports comparing outputs
- Watson Orchestrate endpoint migration
- Rollback snapshot tags

**Success Criteria**:
- Dual-run match rate > 95%
- Migration completed in < 2 weeks
- Zero data loss
- All stakeholder acceptance

---

### Task 007: Hardening & Optimization (`007-hardening-optimization/`)
**Status**: Ready for Phase: context
**Goal**: Production-ready optimizations and performance tuning

**Key Deliverables**:
- Iceberg compaction policies configured
- ZSTD compression tuning (level 3-5)
- Bloom filters on org_id, framework_code, doc_id
- Snapshot retention: 90 days daily + monthly checkpoints
- Full security, hygiene, performance, fuzz gates

**Success Criteria**:
- Query P95 latency < 1 second
- Compaction overhead < 10% of writes
- Storage efficiency > 80%
- All 14 gates passing

---

## Cross-Cutting Concerns

### Authenticity Audit (SCA v13.8-MEA)

**Location**: `../artifacts/authenticity/`
**Completion**: 2025-10-26
**Status**: Baseline captured (203 violations: 34 FATAL, 169 WARN), ready for remediation

A comprehensive authenticity verification system has been implemented to ensure protocol compliance across all production code:

**What It Does**:
- Detects 8 SCA v13.8 protocol violations via pattern-based static analysis
- Scans all production code (apps/, libs/, scripts/, agents/)
- Generates detailed violation reports with file:line references
- Provides remediation guidance for each violation class

**Key Artifacts**:
- **Audit Engine**: `scripts/qa/authenticity_audit.py` (550 LOC, 8 detectors)
- **Test Suite**: `tests/test_authenticity_audit.py` (455 LOC, 28 tests)
- **Full Documentation**: 8 files, 4,100+ lines, 168 KB

**Baseline Findings**:
- **203 total violations**
  - 34 FATAL (eval/exec usage) → Blocks phase validation
  - 169 WARN (time calls, silent exceptions, ordering)
- **Primary Issues**:
  - 76 non-deterministic time calls (blocks determinism proof)
  - 74 silent exception handlers (masks failures)
  - 34 eval/exec usage (security + determinism risk)
  - 9 dict iteration ordering (unpredictable results)
  - 8 JSON-as-Parquet patterns (storage inefficiency)
  - 2 unseeded random calls (non-determinism)

**Remediation Timeline**: 4-7 hours for full compliance

**Quick Links**:
1. **Start Here**: [../artifacts/authenticity/README.md](../artifacts/authenticity/README.md)
   - User guide, usage patterns, troubleshooting

2. **Executive Summary**: [../artifacts/authenticity/ANALYSIS_REPORT.md](../artifacts/authenticity/ANALYSIS_REPORT.md)
   - Detailed findings, impact assessment, remediation strategies

3. **Violations List**: [../artifacts/authenticity/report.json](../artifacts/authenticity/report.json)
   - Machine-readable (file:line references)

4. **Remediation Guide**: [../artifacts/authenticity/REMEDIATION_LOG.md](../artifacts/authenticity/REMEDIATION_LOG.md)
   - Violation-by-violation fix templates, commit conventions

5. **Rollback Procedures**: [../artifacts/authenticity/REVERT_PLAYBOOK.md](../artifacts/authenticity/REVERT_PLAYBOOK.md)
   - Git-based recovery with full examples

6. **Task-Specific Reference**: [018-esg-query-synthesis/qa/AUTHENTICITY_AUDIT.md](018-esg-query-synthesis/qa/AUTHENTICITY_AUDIT.md)
   - How this audit applies to Task 018 implementation

**For All Task Developers**:
- ✓ New code must follow SCA v13.8 patterns to avoid re-introducing violations
- ✓ See "Example: Phase 3 Code Compliance" in `018-esg-query-synthesis/qa/AUTHENTICITY_AUDIT.md`
- ✓ Key patterns: no eval/exec, time overrides, logged exceptions, sorted dict iteration

**Determinism Requirement**:
The audit proves that with SEED=42 and PYTHONHASHSEED=0, the pipeline produces identical outputs on repeated runs (SHA256 hash comparison). This is **non-negotiable for phase validation** under SCA v13.8.

---

## Execution Workflow

### 1. Check Current Task
```bash
cat .sca/profile.json
# Shows current_task and task_sequence
```

### 2. Run Context Phase (for each task)
```bash
cd tasks/001-mcp-iceberg-infrastructure
python ../../sca_infrastructure/runner.py --phase context
```

### 3. Validate Context Gate
All context files must exist and be valid:
- `context/hypothesis.md` - Goals, metrics, critical path
- `context/design.md` - Data strategy, verification plan
- `context/evidence.json` - ≥3 P1 sources
- `context/data_sources.json` - Sources with sha256, pii_flag
- `context/cp_paths.json` - Critical path glob patterns
- `context/adr.md` - Architecture decisions
- `context/assumptions.md` - Migration assumptions

### 4. Execute Phases 1-5 Sequentially
Each phase must pass all 14 gates before proceeding:
- workspace, context, tdd, coverage_cp (≥95%)
- types_cp (mypy --strict), complexity (CCN≤10)
- docs_cp (≥95%), security, hygiene
- authenticity_ast, performance, fuzz
- data_integrity, traceability

### 5. Snapshot Save After Each Phase
```bash
python ../../sca_infrastructure/runner.py --snapshot
```

Creates:
- `artifacts/state.json` - Authoritative state
- `artifacts/memory_sync.json` - Memory synchronization
- `reports/<phase>_snapshot.md` - Phase report
- `context/claims_index.json` - Claims tracking
- `context/executive_summary.md` - Running summary

---

## Traceability Artifacts (Mandatory)

Every run produces:
- `qa/run_log.txt` - Verbatim tool output
- `artifacts/run_context.json` - Run metadata
- `artifacts/run_manifest.json` - Canonical artifact paths
- `artifacts/run_events.jsonl` - Structured event stream

---

## Key Improvements from Current System

1. **Confidence Scoring**: Already improved in `libs/llm/watsonx_client.py`
   - Old: All scores stuck at 50% confidence
   - New: Varies 20-90% based on evidence strength

2. **Real Data**: Using actual sustainability reports via WebSearch
   - Old: Simulated demo data
   - New: Microsoft, Shell, ExxonMobil 2023-2024 reports

3. **Quality Triggers**: MCP fetcher activates when quality < 0.7
   - Old: Manual report fetching
   - New: Automatic quality-based triggering

4. **Traceability**: Full audit trail with Iceberg time-travel
   - Old: No time-travel, no reproducibility
   - New: Every score linked to snapshot ID + AstraDB manifest

5. **Scalability**: Local-first with cloud services only for AI/vector
   - Old: Cloud-dependent
   - New: Runs entirely on laptop, cloud optional

6. **Protocol Compliance**: Proper task structure with all gates enforced
   - Old: Ad-hoc development
   - New: SCA v13.7 full compliance

---

## Next Steps

1. **Update .sca/profile.json** to point to current task
2. **Run context phase** for Task 001
3. **Validate context gate** passes
4. **Implement infrastructure** (Phases 1-5)
5. **Snapshot save** and proceed to Task 002

---

*Generated: 2025-10-21T18:30:00Z*
*Protocol Version: SCA v13.7*
*Task Count: 7*
*Status: All tasks ready for execution*
