# Task 007: Pipeline Orchestration

**Task ID:** 007-pipeline-orchestration
**Protocol:** SCA v13.8-MEA
**Date:** 2025-11-19
**Depends On:** Tasks 003, 004, 005, 006 (ALL COMPLETE)

---

## Objective

Wire Tasks 003-006 into a unified, executable pipeline that chains:

**Ingestion → Extraction → Retrieval → Scoring**

Create a single orchestrator script that takes a ticker symbol (e.g., "AAPL") and outputs a complete ESG maturity score by running the actual verified components from previous tasks.

---

## Input

- **Ticker Symbol:** e.g., "AAPL"
- **Year:** e.g., 2024
- **Raw Data File:** HTML from Task 003 (SEC EDGAR 10-K)

---

## Output

**Final ESG Score JSON:**
```json
{
  "company": "Apple Inc.",
  "ticker": "AAPL",
  "year": 2024,
  "aggregate_maturity": 1.91,
  "maturity_label": "Advanced",
  "confidence": 0.691,
  "dimensions": { ... },
  "evidence_count": 3,
  "execution_timestamp": "..."
}
```

---

## Success Criteria

1. ✅ Single command execution: `python scripts/orchestrate_pipeline.py`
2. ✅ Chains all 4 verified components (no mocks)
3. ✅ Outputs valid ESG score matching Task 006 schema
4. ✅ Completes in < 60 seconds
5. ✅ Full provenance chain maintained

---

## Architecture

```
orchestrate_pipeline.py
    ↓
[1] Load Raw File (Task 003 artifact)
    ↓
[2] Extract Chunks (EnhancedPDFExtractor - Task 004)
    ↓
[3] Index & Retrieve (VectorStore + queries - Task 005)
    ↓
[4] Score Evidence (RubricV3Scorer - Task 006)
    ↓
[5] Output Final Score JSON
```

---

## Protocol Compliance

- **Authenticity:** Uses real components verified in Tasks 003-006
- **Determinism:** Same input file → same output score
- **Traceability:** Full provenance from SEC EDGAR URL to final score
- **Zero Mocks:** All modules are production implementations

---

**Task Status:** INITIALIZED
**Ready for Phase 2:** Implementation
