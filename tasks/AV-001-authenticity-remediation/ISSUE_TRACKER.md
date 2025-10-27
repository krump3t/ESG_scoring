# AV-001: Issue Tracker — Detailed Violation Tracking

**Generated**: 2025-10-26
**Total Issues**: 203
**Status**: 🔴 Ready for Remediation

---

## Progress Summary

```
Overall: [____________________] 0/203 (0%)

Priority 0 (FATAL):      [____________________] 0/34
Priority 1 (Determinism):[____________________] 0/87
Priority 2 (Evidence):   [____________________] 0/29
Priority 3 (Posture):    [____________________] 0/12
Priority 4 (Errors):     [____________________] 0/74
```

---

## Priority 0: FATAL (34 issues) — BLOCKS EVERYTHING

### Category: Unsafe Code Execution (eval/exec)

**F001-F034**: Remove all eval() and exec() calls

| ID | File | Line | Issue | Fix | Status |
|----|------|------|-------|-----|--------|
| F001 | scripts/crawler.py | 42 | `eval(expression)` | Use ast.literal_eval() | ⬜ |
| F002 | scripts/crawler.py | 58 | `exec(code_string)` | Direct function call | ⬜ |
| F003 | scripts/parser.py | 15 | `eval(json_str)` | json.loads() | ⬜ |
| F004 | agents/extraction/extractor.py | 120 | `eval(formula)` | Safe formula parser | ⬜ |
| F005 | agents/extraction/extractor.py | 145 | `exec(template)` | Jinja2 template | ⬜ |
| F006 | agents/normalizer/normalizer.py | 89 | `eval(condition)` | If/else logic | ⬜ |
| F007 | agents/normalizer/normalizer.py | 102 | `exec(script)` | Direct function call | ⬜ |
| F008 | agents/query/query_builder.py | 56 | `eval(query_expr)` | Safe SQL builder | ⬜ |
| F009 | agents/scoring/rubric_scorer.py | 78 | `eval(threshold)` | Float conversion | ⬜ |
| F010 | apps/pipeline/executor.py | 34 | `exec(workflow)` | Direct invocation | ⬜ |
| F011-F034 | (remaining 24) | TBD | eval/exec patterns | Phase 1 work | ⬜ |

**Phase 1 Acceptance Criteria**:
- [ ] All 34 entries have a fix applied
- [ ] `grep -r "eval\|exec" scripts/ agents/ apps/ libs/` returns 0 results
- [ ] All tests still pass (no functionality broken)
- [ ] Each fix documented in commit message
- [ ] All 34 violations marked ✅ DONE

---

## Priority 1: Determinism (87 issues) — REGULATORY RISK

### Category: Unseeded Randomness

| Module | Count | Examples | Fix | Status |
|--------|-------|----------|-----|--------|
| agents/embedding/ | 12 | `random.shuffle()`, `np.random.choice()` | Use `get_seeded_random()` | ⬜ |
| agents/retrieval/ | 18 | `random.sample()`, `random.randint()` | Initialize SEED in __init__ | ⬜ |
| agents/ranking/ | 15 | `random.random()`, `shuffle()` | Use seeded instance | ⬜ |
| libs/llm/ | 22 | `temperature=random()`, `top_p random` | Use SEED in config | ⬜ |
| scripts/ | 20 | Random sampling, shuffling | Add seed config | ⬜ |

### Category: Non-Deterministic Time Operations

| Module | Count | Examples | Fix | Status |
|--------|-------|----------|-----|--------|
| agents/ | 8 | `datetime.now()`, `time.time()` | Use `get_clock()` | ⬜ |
| apps/ | 7 | `time.time()` in logging | Use Clock abstraction | ⬜ |
| libs/ | 5 | Timestamp generation | FIXED_TIME env var | ⬜ |

**Phase 2 Acceptance Criteria**:
- [ ] All 87 entries addressed
- [ ] `export FIXED_TIME=1729000000.0 SEED=42` set in environment
- [ ] 3x determinism test: `bash /tmp/test_det.sh` = byte-identical outputs
- [ ] All tests still pass
- [ ] Each module imports from libs/utils/{clock,determinism}.py

---

## Priority 2: Evidence & Parity (29 issues) — COMPLIANCE RISK

### Category: Rubric Compliance (MIN_QUOTES enforcement)

| Issue | Description | Fix | Status |
|-------|-------------|-----|--------|
| E01 | Evidence without ≥2 quotes scored above Stage 0 | Enforce MIN_QUOTES_PER_THEME = 2 | ⬜ |
| E02-E15 | (14 instances) | Review evidence records | Add validation tests | ⬜ |

### Category: Parity Validation (evidence ⊆ retrieval)

| Issue | Description | Fix | Status |
|-------|-------------|-----|--------|
| E16 | Evidence used not in top-k results | Add ParityChecker validation | ⬜ |
| E17-E25 | (9 instances) | Validate evidence subset | Add parity gates | ⬜ |

### Category: Evidence Contract (required fields)

| Issue | Description | Fix | Status |
|-------|-------------|-----|--------|
| E26 | Missing extract_30w in evidence | Add validation schema | ⬜ |
| E27-E29 | (3 instances) | Missing doc_id, theme_code | Enforce contract | ⬜ |

**Phase 3 Acceptance Criteria**:
- [ ] All 29 entries addressed
- [ ] RubricScorer enforces MIN_QUOTES_PER_THEME = 2
- [ ] ParityChecker validates evidence ⊆ top-k
- [ ] All evidence records have required fields
- [ ] `python scripts/qa/verify_parity.py` = PASS
- [ ] All tests pass

---

## Priority 3: Production Posture (12 issues) — PRODUCTION RISK

### Category: Type Safety (mypy --strict)

| Issue | File | Problem | Fix | Status |
|-------|------|---------|-----|--------|
| P01 | apps/api/main.py | Missing return type annotation | Add `-> TraceResponse` | ⬜ |
| P02 | agents/scoring/rubric_scorer.py | Optional without Union | Add Optional[...] | ⬜ |
| P03 | libs/retrieval/parity_checker.py | Implicit Any | Add explicit types | ⬜ |
| P04-P08 | (5 instances) | Type annotation gaps | Run mypy --strict | ⬜ |

### Category: Error Handling & Docker Compliance

| Issue | Category | Problem | Fix | Status |
|-------|----------|---------|-----|--------|
| P09 | API errors | Missing try/except | Add error handlers | ⬜ |
| P10 | Network calls | Not Docker-only | Remove/mock | ⬜ |
| P11 | File I/O | No error recovery | Add graceful degradation | ⬜ |
| P12 | Validation | Missing input checks | Add schema validation | ⬜ |

**Phase 4 Acceptance Criteria**:
- [ ] All 12 entries addressed
- [ ] `mypy --strict` = 0 errors
- [ ] All API endpoints have error handling
- [ ] No external network calls in production code
- [ ] Docker offline test: `docker run --network none esg-scorer /trace` = 200 OK
- [ ] All tests pass

---

## Priority 4: Silent Failures (74 issues) — ROBUSTNESS RISK

### Category: Missing Exception Handlers

| Module | Count | Pattern | Fix | Status |
|--------|-------|---------|-----|--------|
| scripts/ | 20 | Missing try/except | Add handlers + logging | ⬜ |
| agents/ | 30 | Silent exception swallowing | Log before continuing | ⬜ |
| apps/ | 15 | Unhandled API errors | Return 500 + log | ⬜ |
| libs/ | 9 | File not found not handled | Graceful recovery | ⬜ |

### Category: Insufficient Logging

| Module | Count | Issue | Fix | Status |
|--------|-------|-------|-----|--------|
| agents/ | 20 | No logging in critical paths | Add info/warning logs | ⬜ |
| apps/ | 15 | No request/response logging | Log all API calls | ⬜ |
| libs/ | 9 | No debug logs for troubleshooting | Add debug statements | ⬜ |

### Category: Status Code Not Returned

| Module | Count | Issue | Fix | Status |
|--------|-------|-------|-----|--------|
| apps/api | 10 | Missing 404/500 responses | Add explicit status codes | ⬜ |

**Phase 5 Acceptance Criteria**:
- [ ] All 74 entries addressed
- [ ] `grep -rn "except.*:" scripts/ agents/` shows logging in each block
- [ ] All exceptions explicitly handled (no silent failures)
- [ ] `pytest tests/ -k error` = all pass
- [ ] Coverage ≥95% on modified files
- [ ] All tests pass

---

## Phase 6: Final Verification (1 issue)

### V001: Audit Compliance

| Criterion | Target | Verification Command | Status |
|-----------|--------|----------------------|--------|
| Total Violations | 0 | `python scripts/qa/authenticity_audit.py \| jq length` | ⬜ |
| FATAL Violations | 0 | `grep -c '"severity": 0' artifacts/audit_final.json` | ⬜ |
| Test Pass Rate | 523/523 | `pytest tests/ --cov` | ⬜ |
| Type Safety | 0 errors | `mypy --strict apps/ agents/ libs/ scripts/` | ⬜ |
| Coverage | ≥95% | `pytest --cov-report=term \| grep TOTAL` | ⬜ |
| Determinism | 3x identical | `bash /tmp/test_det.sh` | ⬜ |
| Docker Offline | Working | `docker run --network none esg-scorer /trace` | ⬜ |
| Git Tags | Present | `git tag \| grep audit` | ⬜ |

**Phase 6 Acceptance Criteria**:
- [ ] All verification commands pass
- [ ] Completion report generated
- [ ] Final commit tagged: v1.0.0-audit-clean
- [ ] All work pushed to repository

---

## Daily Progress Tracking

### Day 1 Targets
```
Target: Fix Priority 0 (FATAL) + Priority 1 (Determinism)
Issues: 34 + 87 = 121 out of 203 (60%)
Time: 7-12 hours

Actual:
  - Time spent: ___ hours
  - Issues fixed: ___/121
  - Tests passing: ___/523
  - Commits: ___
```

### Day 2 Targets
```
Target: Fix Priority 2 (Evidence) + Priority 3 (Posture)
Issues: 29 + 12 = 41 out of remaining 82 (50%)
Time: 7-10 hours

Actual:
  - Time spent: ___ hours
  - Issues fixed: ___/41
  - Tests passing: ___/523
  - Commits: ___
```

### Day 3 Targets
```
Target: Fix Priority 4 (Errors) + Phase 6 (Verify)
Issues: 74 + 1 = 75 out of remaining 41 (100%)
Time: 3-6 hours

Actual:
  - Time spent: ___ hours
  - Issues fixed: ___/75
  - Tests passing: ___/523
  - Final audit: ___/203 violations
```

---

## Issue Status Legend

| Status | Meaning | Action |
|--------|---------|--------|
| ⬜ | Not Started | Waiting for phase |
| 🟨 | In Progress | Currently working on |
| ✅ | Done | Verified & committed |
| ❌ | Blocked | See TROUBLESHOOTING_GUIDE.md |

---

## Quick Links by Phase

- **Phase 1 (FATAL)**: See "Priority 0" section above
- **Phase 2 (Determinism)**: See "Priority 1" section above
- **Phase 3 (Evidence)**: See "Priority 2" section above
- **Phase 4 (Posture)**: See "Priority 3" section above
- **Phase 5 (Errors)**: See "Priority 4" section above
- **Phase 6 (Verify)**: See "Phase 6: Final Verification" section above

---

## Velocity Tracking

| Metric | Day 1 Target | Actual | Day 2 Target | Actual | Day 3 Target | Actual |
|--------|--------------|--------|--------------|--------|--------------|--------|
| Issues Fixed | 121 | ___ | 41 | ___ | 75 | ___ |
| Time Spent | 7-12h | ___ | 7-10h | ___ | 3-6h | ___ |
| Tests Passing | 523 | ___ | 523 | ___ | 523 | ___ |
| Commits | 6-10 | ___ | 6-8 | ___ | 5-7 | ___ |

---

## Final Sign-Off

```
✅ All 34 FATAL violations (Priority 0) resolved
✅ All 87 Determinism violations (Priority 1) resolved
✅ All 29 Evidence violations (Priority 2) resolved
✅ All 12 Posture violations (Priority 3) resolved
✅ All 74 Error violations (Priority 4) resolved
✅ Final Verification (Phase 6) complete

Total Violations Fixed: 203/203 (100%)
Final Status: 🚀 PRODUCTION READY
```

---

## Document Info

**Title**: AV-001 Issue Tracker
**Version**: 1.0
**Created**: 2025-10-26
**Last Updated**: _______
**Protocol**: SCA v13.8-MEA
**Status**: Ready for execution

---

**Update this tracker daily as you progress through remediation. Track each issue (F001-F034 for Phase 1, then D001-D087 for Phase 2, etc.). All 203 issues resolved = success.**
