# AR-001: Authenticity Refactor Hypothesis

## Objective
Implement the 5 authenticity gates required by SCA v13.8-MEA for the ESG prospecting engine:
1. **ingestion_authenticity**: Crawl ledger with URL, headers, SHA256
2. **parity**: Evidence ⊆ fused top-k invariant
3. **rubric_compliance**: ≥2 quotes per theme enforcement
4. **determinism**: 3× identical outputs
5. **docker_only**: Runtime read-only scoring, no network egress

## Metrics & Thresholds
- **Coverage (CP)**: ≥95% line & branch on all CP modules
- **Type Safety**: `mypy --strict` = 0 errors on CP
- **Complexity**: Lizard CCN ≤ 10; Cognitive ≤ 15
- **Docs**: `interrogate` ≥ 95%
- **Determinism**: 3× identical runs → byte-identical artifacts/maturity.parquet & run_manifest.json
- **Parity**: evidence_ids ⊆ fused_top_5_ids for 100% of demo queries

## Critical Path Files
- `agents/crawler/ledger.py`: IngestLedger class (≥1 test, ≥1 Hypothesis test, ≥1 failure-path test)
- `agents/scoring/rubric_scorer.py`: RubricScorer with ≥2 quotes enforcement (≥1 test, ≥1 Hypothesis test)
- `libs/retrieval/parity_checker.py`: ParityChecker for evidence ⊆ top-k validation
- `apps/api/main.py`: /trace endpoint for traceability audit

## Test Fixtures
- `tests/authenticity/test_ingestion_authenticity_cp.py`
- `tests/authenticity/test_parity_gate_cp.py`
- `tests/authenticity/test_rubric_compliance_cp.py`
- `tests/authenticity/test_determinism_cp.py`

## Power & Confidence
- **Confidence Interval (CI)**: 95%
- **Power**: 0.95 (detect 5% difference in metrics)
- **Sample Size**: 3× runs per artifact determinism test

## Risks & Exclusions
- **Risk**: ParityChecker may not catch all query types → mitigate with batch tests
- **Exclusion**: Docker-only gate not tested in local dev (requires container runtime)
