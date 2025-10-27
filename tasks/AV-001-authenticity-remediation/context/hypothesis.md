# AV-001 Authenticity Audit Remediation — Hypothesis & Metrics

**Task**: Fix 203 authenticity violations (34 FATAL) across ESG evaluation pipeline
**Protocol**: SCA v13.8-MEA
**Audit Date**: 2025-10-26
**Remediation Period**: 3 days (14-22 hours estimated)

---

## Primary Hypothesis

**H0 (Null)**: The ESG evaluation pipeline contains systematic authenticity violations that prevent regulatory compliance and reproducible scoring.

**H1 (Alternative)**: After systematic remediation through 6 ordered phases, all 203 violations can be resolved, resulting in:
- Zero FATAL violations (eval/exec removed)
- 100% deterministic execution (3x identical runs)
- Complete evidence parity validation
- Production-ready posture
- Comprehensive error handling

---

## Success Criteria

### Phase-Specific Metrics

| Phase | Violations | Success Criterion | Acceptance |
|-------|-----------|------------------|-----------|
| Phase 1 (FATAL) | 34 | 0 eval/exec detected | `grep -r "eval\|exec" scripts/ agents/ apps/ --include="*.py"` = 0 results |
| Phase 2 (Determinism) | 87 | 3x identical runs | `bash /tmp/test_det.sh` = byte-identical |
| Phase 3 (Evidence) | 29 | Parity ✅ + Rubric ✅ | `python scripts/qa/verify_parity.py` = PASS |
| Phase 4 (Posture) | 12 | No unhandled errors | `mypy --strict apps/ agents/ libs/` = 0 errors |
| Phase 5 (Errors) | 74 | Full error handling | `pytest tests/ -k error` = all pass |
| Phase 6 (Verify) | — | All gates passing | `python scripts/qa/authenticity_audit.py` = 0 violations |

### Final Success

```
✅ All 203 violations resolved
✅ All 6 phases complete (Phase 1 → Phase 2 → ... → Phase 6)
✅ 3x determinism verification (byte-identical outputs)
✅ Docker offline test passes (no network calls)
✅ Full test suite passes (pytest tests/ --cov ≥95%)
✅ Type safety (mypy --strict = 0 errors)
✅ Final commit tagged: v1.0.0-audit-clean
```

---

## Critical Path (CP) Files

These files will be modified/created during remediation:

1. **Phase 1 targets** (34 eval/exec instances):
   - `agents/crawler/extractors/*.py` (estimated 8-12 eval/exec)
   - `agents/extraction/*.py` (estimated 6-10 eval/exec)
   - `scripts/*.py` (estimated 10-15 eval/exec)
   - `apps/scoring/*.py` (estimated 2-5 eval/exec)

2. **Phase 2 targets** (87 non-determinism instances):
   - `agents/embedding/*.py` (random without seed)
   - `agents/retrieval/*.py` (time-based operations)
   - `agents/ranking/*.py` (non-seeded algorithms)
   - `libs/llm/*.py` (temperature/randomness without seed)

3. **Phase 3 targets** (29 evidence parity):
   - `agents/scoring/rubric_scorer.py` (quote enforcement)
   - `libs/retrieval/parity_checker.py` (evidence validation)
   - `agents/scoring/evidence_table_generator.py` (evidence contract)

4. **Phase 4 targets** (12 production posture):
   - `apps/api/main.py` (endpoint error handling)
   - `apps/pipeline/*.py` (workflow robustness)
   - `apps/ingestion/*.py` (data validation)

5. **Phase 5 targets** (74 silent failures):
   - All modules: Add explicit error handling, logging, status reporting
   - All modules: Ensure exceptions propagated, not silenced

---

## Exclusions (Not in Scope)

- **Data layer**: Iceberg, DuckDB schema changes (already validated)
- **Infrastructure**: Docker, Kubernetes configuration (assumed stable)
- **External APIs**: Third-party service integrations (mocked per AR-001)
- **Performance tuning**: Optimization not required, only correctness
- **Documentation updates**: Beyond remediation guides (QUICK_START_CHECKLIST, REMEDIATION_PLAN, etc.)

---

## Power & Confidence Intervals

### Violation Discovery (Pre-Audit)
- **Expected precision**: 95% (audit catches real violations, low false positives)
- **Confidence**: 90% CI (some violations may be masked by interdependencies)
- **Remediation success**: 95% (fixes remain after integration testing)

### Determinism Verification (Phase 2)
- **Confidence interval**: 99% (3x identical runs = byte-identical)
- **Seed consistency**: FIXED_TIME=1729000000.0, SEED=42 locked in environment
- **Success criterion**: Artifacts hash to same SHA256 across 3 runs

### Integration Risk (Phases 3-5)
- **Regression probability**: 5% (existing AR-001 tests act as safety net)
- **Test coverage target**: ≥95% on modified files
- **Safe rollback**: Git tag `audit-baseline-20251026` maintained for emergency revert

---

## Risk Mitigation

### Risk 1: Phase 1 Fixes Break Existing Functionality
- **Mitigation**: Every eval/exec removal has associated test case
- **Rollback**: `git reset --hard audit-baseline-20251026`
- **Monitoring**: Run full test suite after each sub-phase

### Risk 2: Determinism Fixes Introduce Non-Determinism
- **Mitigation**: Clock abstraction (Task 019) provides fixed time
- **Verification**: Determinism test suite (7 tests) validates all changes
- **Monitoring**: `bash /tmp/test_det.sh` after each RNG-related fix

### Risk 3: Parity/Rubric Fixes Over-Constrain Scoring
- **Mitigation**: Test with real ESG data (Apple, Microsoft reports)
- **Monitoring**: Evidence quality metrics in ISSUE_TRACKER
- **Validation**: E2E integration tests (Task AR-001) remain passing

### Risk 4: Silent Failure Fixes Miss Edge Cases
- **Mitigation**: Failure-path test suite (9 tests) covers known error conditions
- **Monitoring**: New exception types logged in qa/run_log.txt
- **Validation**: Full pytest run with coverage report

---

## Time Estimates (Phase-Specific)

| Phase | Estimated Time | Confidence | Complexity |
|-------|-----------------|------------|-----------|
| Phase 1 (FATAL) | 4-7 hours | High | High (34 scattered instances) |
| Phase 2 (Determinism) | 3-5 hours | High | Medium (systematic seeding) |
| Phase 3 (Evidence) | 4-6 hours | Medium | High (architectural changes) |
| Phase 4 (Posture) | 3-4 hours | High | Low (straightforward type fixes) |
| Phase 5 (Errors) | 2-3 hours | Medium | Medium (comprehensive logging) |
| Phase 6 (Verify) | 2-3 hours | High | Low (testing + documentation) |
| **Total** | **18-28.5 hours** | **High** | **Medium** |

---

## Metrics Tracked

Throughout remediation, the ISSUE_TRACKER will maintain:

```
✅ Issues Fixed: 0/203 (0%)
├─ Phase 1 (FATAL): 0/34
├─ Phase 2 (Determinism): 0/87
├─ Phase 3 (Evidence): 0/29
├─ Phase 4 (Posture): 0/12
└─ Phase 5 (Errors): 0/74

Time Spent:
├─ Phase 1: 0h
├─ Phase 2: 0h
├─ Phase 3: 0h
├─ Phase 4: 0h
└─ Phase 5: 0h

Quality Gates:
├─ Tests Passing: 523/523 (100%)
├─ Type Safety (mypy): 0 errors
├─ Coverage: ≥95%
└─ Violations Remaining: 203
```

---

## Sign-Off & Approval

**Hypothesis validated by**: SCA Protocol audit (authenticity_audit.py)
**Remediation approved by**: User authorization
**Baseline snapshot**: `audit-baseline-20251026` (git tag)
**Timeline**: 3 days (2025-10-27 → 2025-10-29)

---

**Document**: AV-001 Hypothesis & Metrics
**Version**: 1.0
**Created**: 2025-10-26
