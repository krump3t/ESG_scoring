# Task 019: Authenticity Infrastructure & System-Wide Remediation — Hypothesis & Metrics

**Task ID**: 019-authenticity-infrastructure
**Phase**: Foundation (Infrastructure Layer)
**Status**: Context Gate (awaiting validation)
**Dependencies**: Authenticity Audit (AV-001) ✓ COMPLETE

---

## Primary Claim

**Task 019 will establish determinism infrastructure (Clock, RNG, HTTP abstraction) and systematically remediate all 149 authenticity violations identified in the comprehensive audit, achieving full SCA v13.8 compliance with zero FATAL violations and fewer than 5 documented WARN violations.**

---

## Success Criteria (SC19.1-SC19.6)

| SC | Criterion | Target | Validation Method |
|----|-----------|--------|-------------------|
| SC19.1 | Authenticity audit status | status="ok", 0 FATAL violations | Run `python scripts/qa/authenticity_audit.py` |
| SC19.2 | Deterministic behavior | SEED=42 produces identical outputs across 10 runs | Hash stability test (SHA256 comparison) |
| SC19.3 | Clock abstraction coverage | 100% of 81 time violations remediated | Code review + grep validation |
| SC19.4 | HTTP abstraction coverage | 100% of 33 network violations remediated | Test suite: zero live HTTP calls |
| SC19.5 | Exception handling | 0 silent exception handlers in production CP code | AST scan + code review |
| SC19.6 | Coverage (infrastructure) | ≥95% line & branch on libs/utils/* CP modules | pytest-cov report |

---

## Key Metrics

### Functional Metrics (Authenticity Remediation)
- **Authenticity violations**: 149 → 11 exempted, 138 remediated (target: 0 production FATAL, 11 documented exemptions)
  - FATAL: 9 → 1 production FIX, 8 test-only EXEMPT (eval_exec: 6, workspace_escape: 2)
  - WARN: 140 → 135 remediated, 5 test-only EXEMPT (to_json in test fixtures: 3, audit meta-code: 2)
- **Determinism test**: 10 consecutive runs with SEED=42 produce identical SHA256 hash
- **Network isolation**: Zero live HTTP calls in test suite (100% fixture-based)
- **Clock injection coverage**: 81 datetime.now()/time.time() calls → Clock abstraction
- **HTTP injection coverage**: 33 requests imports → HTTPClient abstraction

### Quality Metrics (Infrastructure Modules)
- **Type hints coverage**: 100% on CP files (libs/utils/clock.py, determinism.py, http_client.py)
- **Docstring coverage**: 100% (module + function level, interrogate)
- **Test coverage**: ≥95% line & branch on CP files
- **Cyclomatic complexity**: ≤10 per function (lizard)
- **Cognitive complexity**: ≤15 per function

### Authenticity Metrics
- **Real infrastructure**: Actual Clock/RNG/HTTP abstractions (no mocks in production)
- **Real audit data**: Authentic violation data from `artifacts/authenticity/report.json`
- **Real differential testing**: Compare behavior with/without FIXED_TIME environment variable
- **Real determinism validation**: Execute same workflow 10x with fixed seed, verify byte-for-byte reproducibility

---

## Critical Path (CP) Modules

**Infrastructure Layer** (foundational utilities):

1. **libs/utils/clock.py** — Deterministic time abstraction
   - `Clock` class with `now()` (datetime) and `time()` (float) methods
   - Dependency injection via `get_clock()` / `set_clock()`
   - Environment variable support: `FIXED_TIME` for deterministic testing
   - Type hints: 100% | Docstrings: complete
   - **LOC estimate**: ~150

2. **libs/utils/determinism.py** — Seeded randomness utilities
   - `get_seeded_random()` factory function (uses SEED env var)
   - Global seed initialization from `PYTHONHASHSEED`
   - Reproducibility helpers for numpy/random modules
   - Type hints: 100% | Docstrings: complete
   - **LOC estimate**: ~80

3. **libs/utils/http_client.py** — HTTP client abstraction for testability
   - `HTTPClient` ABC with `get()`, `post()` methods
   - `RealHTTPClient` (production, uses requests library)
   - `MockHTTPClient` (testing, fixture-based responses)
   - Fixture registry: `fixtures/http_responses/*.json`
   - Type hints: 100% | Docstrings: complete
   - **LOC estimate**: ~200

4. **.sca/exemptions.json** — Authenticity violation exemption registry
   - JSON format with file, line, violation_type, justification, expiry
   - Used by `scripts/qa/authenticity_audit.py` to filter approved exceptions
   - Type hints: N/A | Schema validation: required
   - **LOC estimate**: ~50 lines (JSON)

---

## Exclusions & Exemptions

### Approved Exclusions (11 Total)

**Test-Only FATAL Exemptions (8)**:
1. **eval_exec in audit detector**: `scripts/qa/authenticity_audit.py`
   - Lines: 306, 322 (detector pattern definitions, not code execution)
   - Justification: Meta-programming for violation detection
   - Expiry: Permanent

2. **eval_exec in audit tests**: `tests/test_authenticity_audit.py`
   - Lines: 273, 275, 283, 285 (test cases validating eval/exec detection)
   - Justification: Security test coverage for detector
   - Expiry: Permanent

3. **workspace_escape in audit tests**: `tests/test_authenticity_audit.py`
   - Lines: 212, 222 (test cases validating path traversal detection)
   - Justification: Security test coverage for detector
   - Expiry: Permanent

**Test-Only WARN Exemptions (3)**:
4. **to_json in test fixtures**: `tests/scoring/test_rubric_models.py`
   - Lines: 385, 407, 435 (test fixtures for human readability, not data artifacts)
   - Justification: Test readability, not production data processing
   - Expiry: 2026-06-01

**Summary**:
- 8 FATAL exemptions (all in test files: 6 eval_exec, 2 workspace_escape)
- 3 WARN exemptions (all in test files: to_json for fixtures)
- 0 production code exemptions
- All exemptions documented in `.sca/exemptions.json` with expiry dates

### Power Analysis & Confidence Intervals
- **Sample size**: 149 violations (full codebase scan)
- **Expected remediation**: 138 violations (92.6%)
- **Exempted**: 11 violations (7.4%, all test-only, all documented)
- **Production violations remediated**: 100% (1 FATAL, 135 WARN)
- **Confidence level**: 100% (deterministic audit, not statistical sample)
- **Risk mitigation**: Differential testing + 10-run determinism validation

---

## Inputs & Outputs

### Inputs
1. **Authenticity Audit Report**: `artifacts/authenticity/report.json`
   - 149 violations with file/line/type/severity
   - SHA256: (to be computed on read)
   - Generated: 2025-10-26T23:12:40.467805Z

2. **Existing Codebase**: All production and test files with violations
   - 81 datetime.now()/time.time() calls
   - 33 direct `requests` imports
   - 1 unseeded `random.randint()` (FATAL)
   - 10 silent exception handlers

### Outputs
1. **Infrastructure Modules**: libs/utils/{clock, determinism, http_client}.py
2. **Remediated Codebase**: 138 violations fixed (11 exempted)
3. **Post-Remediation Audit**: `artifacts/authenticity/report_post_remediation.json`
4. **Determinism Validation**: `artifacts/determinism/hash_stability.json`
   - 10 SHA256 hashes from identical runs with SEED=42
   - Expected: All hashes identical
5. **Exemption Registry**: `.sca/exemptions.json` (11 documented exemptions: 8 FATAL test-only, 3 WARN test-only)

---

## Verification Strategy

### 1. Determinism Test (SC19.2)
**Procedure**:
```bash
export SEED=42
export FIXED_TIME=1609459200  # 2021-01-01 00:00:00 UTC
for i in {1..10}; do
  python scripts/test_determinism.py > run_$i.log
  sha256sum run_$i.log >> hashes.txt
done
# Verify all 10 hashes are identical
```

**Acceptance**: All 10 SHA256 hashes match

### 2. Differential Test (Clock Abstraction)
**Procedure**:
```bash
# Run with FIXED_TIME
FIXED_TIME=1609459200 python scripts/compare_esg_analysis.py > output_fixed.json

# Run without FIXED_TIME (real clock)
python scripts/compare_esg_analysis.py > output_real.json

# Verify timestamps differ, but logic identical
```

**Acceptance**: Outputs differ only in timestamp fields

### 3. Network Isolation Test (SC19.4)
**Procedure**:
```bash
# Run test suite without network access
pytest --tb=short 2>&1 | grep -i "connection\|socket\|network"
```

**Acceptance**: Zero network errors (all tests use MockHTTPClient)

### 4. Coverage Validation (SC19.6)
**Procedure**:
```bash
pytest tests/utils/ --cov=libs/utils --cov-branch --cov-report=term-missing
```

**Acceptance**: ≥95% line & branch coverage on CP files

### 5. Authenticity Audit Re-run (SC19.1)
**Procedure**:
```bash
export PYTHONHASHSEED=0
export ESG_ROOT="$(pwd)"
python scripts/qa/authenticity_audit.py
```

**Acceptance**: `status: "ok"`, 0 FATAL, ≤5 WARN (all in `.sca/exemptions.json`)

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Clock injection breaks existing tests | Medium | High | Phase-by-phase rollout with per-module testing |
| HTTP fixtures incomplete for all use cases | Low | Medium | Generate fixtures from live API captures (one-time) |
| Determinism test fails on OS-specific code | Low | High | Use platform-agnostic algorithms; document OS-specific exemptions |
| Exemption registry becomes stale | Medium | Low | Add expiry dates; automated check in CI |
| Rollout causes regressions | Medium | High | Git branching; rollback plan per phase |

---

## Timeline & Phases

**Total Effort**: ~43 hours over 3-week sprint (Sprint 3)

| Phase | Focus | Effort | Week |
|-------|-------|--------|------|
| 1 | FATAL fix (unseeded random) | 2h | Week 1, Day 1 |
| 2 | Clock abstraction (81 violations) | 16h | Week 1, Days 2-5 |
| 3 | HTTP abstraction (33 violations) | 12h | Week 2, Days 6-10 |
| 4 | Exception handling (10 violations) | 4h | Week 2, Days 11-12 |
| 5 | Parquet migration (16 violations) | 6h | Week 3, Days 13-15 |
| 6 | Task 018 coverage fix | 3h | Week 3, Days 16-17 |
| Validation | Final audit + determinism test | 2h | Week 3, Days 18-21 |

---

## Dependencies

**Upstream** (must be complete before Task 019):
- ✓ Authenticity audit (AV-001) - COMPLETE (2025-10-26)
- ✓ AUTHENTICITY_REMEDIATION_PLAN.md - COMPLETE (2025-10-26)

**Downstream** (blocked until Task 019 complete):
- Task 020+: All future tasks benefit from determinism infrastructure
- Production deployment: Requires FIXED_TIME capability for reproducible testing

---

**End of hypothesis.md**
