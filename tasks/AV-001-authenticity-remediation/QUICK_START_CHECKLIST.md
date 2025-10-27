# AV-001: Quick Start Checklist — Daily Task List

**Status**: 🔴 Ready to Begin
**Start Date**: 2025-10-27
**Target End Date**: 2025-10-29
**Total Violations**: 203

---

## Progress Dashboard

```
Overall Progress: [____________________] 0/203 (0%)

Phase 1 (FATAL):      [____________________] 0/34
Phase 2 (Determinism):[____________________] 0/87
Phase 3 (Evidence):   [____________________] 0/29
Phase 4 (Posture):    [____________________] 0/12
Phase 5 (Errors):     [____________________] 0/74
Phase 6 (Verify):     [____________________] 0/1
```

---

## Day 1: FATAL + Determinism (7-12 hours)

### Morning: Phase 1 — Remove eval/exec (4-7 hours)

**Objective**: Find and replace all 34 eval/exec instances

**Pre-flight Checklist**:
- [ ] Git baseline created: `git tag audit-baseline-20251026`
- [ ] All tests passing: `pytest tests/ --cov` = 523/523
- [ ] Audit baseline captured: `python scripts/qa/authenticity_audit.py > artifacts/audit_phase0.json`
- [ ] Read EXECUTIVE_SUMMARY.md (done ✅)
- [ ] This is Day 1 morning (you're here now)

**Task 1.1: Identify all eval/exec instances** (15 min)
```bash
# Find all eval calls
grep -rn "eval(" scripts/ agents/ apps/ libs/ --include="*.py" > /tmp/eval_findings.txt
wc -l /tmp/eval_findings.txt
# Expected: ~17-20 instances

# Find all exec calls
grep -rn "exec(" scripts/ agents/ apps/ libs/ --include="*.py" > /tmp/exec_findings.txt
wc -l /tmp/exec_findings.txt
# Expected: ~14-17 instances

# Total expected: 34 instances
```

**Task 1.2: Fix eval/exec batch 1** (60-90 min)
- [ ] Open first eval instance in REMEDIATION_PLAN.md (Phase 1.1)
- [ ] Identify file and line number
- [ ] Review suggested replacement
- [ ] Apply fix
- [ ] Test: `pytest tests/ -k <module>` (just that module)
- [ ] Commit: `git commit -m "fix(AV-001-F001): Remove eval() in <file>:<line>"`
- [ ] Mark issue in ISSUE_TRACKER.md as DONE
- [ ] Repeat for 3-4 instances (estimate 60-90 min)

**Task 1.3: Check progress** (5 min)
```bash
# Re-run eval/exec check
grep -r "eval\|exec" scripts/ agents/ apps/ libs/ --include="*.py" | wc -l
# Should have decreased from 34
```

**Task 1.4: Fix eval/exec batch 2** (60-90 min)
- [ ] Repeat Task 1.2 for next batch (3-4 instances)
- [ ] Test after each fix
- [ ] Commit with issue ID
- [ ] Update ISSUE_TRACKER.md

**Task 1.5: Final eval/exec check** (30 min)
- [ ] Remaining eval/exec instances (≤4)
- [ ] Apply fixes
- [ ] Verify: `grep -r "eval\|exec" scripts/ agents/ apps/ libs/ --include="*.py"` = 0 results
- [ ] Commit final batch
- [ ] Update ISSUE_TRACKER.md: Phase 1 = DONE

**Task 1.6: Audit Phase 1 completion** (10 min)
```bash
# Run audit after Phase 1
python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase1.json

# Verify FATAL violations gone
grep -c '"severity": 0' artifacts/audit_after_phase1.json
# Expected: 0

# Check total violations reduced
python -c "
import json
before = len(json.load(open('artifacts/audit_phase0.json')))
after = len(json.load(open('artifacts/audit_after_phase1.json')))
print(f'Violations: {before} → {after} (fixed {before-after})')
"
# Expected: 203 → ~169 (34 fixed)

# Run full test suite
pytest tests/ --cov
# Expected: 523/523 pass ✅
```

**End of Morning Checklist**:
- [ ] 34 eval/exec instances removed
- [ ] 0 FATAL violations remaining
- [ ] All 523 tests passing
- [ ] Phase 1 audit snapshot saved
- [ ] All work committed with issue IDs

---

### Afternoon: Phase 2 — Determinism (3-5 hours)

**Objective**: Seed all randomness, fix non-determinism

**Task 2.1: Identify unseeded randomness** (15 min)
```bash
# Find random calls without seed
grep -rn "random\|shuffle\|sample" scripts/ agents/ apps/ libs/ --include="*.py" \
  | grep -v "seed\|SEED\|determinism" > /tmp/random_findings.txt
wc -l /tmp/random_findings.txt
# Expected: ~80-95 instances
```

**Task 2.2: Add SEED initialization** (60 min)
- [ ] Find module with random imports
- [ ] Add at top of module: `from libs.utils.determinism import initialize_numpy_seed, get_seeded_random`
- [ ] Add to initialization: `initialize_numpy_seed()` (once per module)
- [ ] Test: `pytest tests/ -k <module>`
- [ ] Commit: `git commit -m "fix(AV-001-D01): Seed randomness in <module>"`
- [ ] Update ISSUE_TRACKER.md

**Task 2.3: Fix time-based operations** (60 min)
- [ ] Find datetime/time imports
- [ ] Add: `from libs.utils.clock import get_clock`
- [ ] Replace `datetime.now()` with `get_clock().now()`
- [ ] Replace `time.time()` with `get_clock().time()`
- [ ] Test after each module
- [ ] Commit: `git commit -m "fix(AV-001-T01): Use Clock abstraction in <module>"`

**Task 2.4: Determinism validation** (30-60 min)
```bash
# Create determinism test script
cat > /tmp/test_det.sh << 'EOF'
#!/bin/bash
export FIXED_TIME=1729000000.0
export SEED=42

for i in {1..3}; do
  python scripts/evaluate.py > /tmp/run_$i.json 2>&1
  sha256sum /tmp/run_$i.json | awk '{print $1}' >> /tmp/run_hashes.txt
done

# Check if all 3 are identical
if [[ $(sort -u /tmp/run_hashes.txt | wc -l) -eq 1 ]]; then
  echo "✅ DETERMINISM PASS: 3 runs byte-identical"
else
  echo "❌ DETERMINISM FAIL: Runs differ"
  cat /tmp/run_hashes.txt
fi
EOF

chmod +x /tmp/test_det.sh
bash /tmp/test_det.sh
# Expected: ✅ DETERMINISM PASS
```

**Task 2.5: Phase 2 completion audit** (10 min)
```bash
# Audit after Phase 2
python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase2.json

# Verify determinism violations fixed
grep '"type": "DETERMINISM"' artifacts/audit_after_phase2.json | wc -l
# Expected: 0 or near 0

# Run tests
pytest tests/ --cov
# Expected: 523/523 pass ✅
```

**End of Afternoon Checklist**:
- [ ] All unseeded randomness fixed
- [ ] All time-based ops use Clock abstraction
- [ ] 3x determinism test = byte-identical
- [ ] Phase 2 audit snapshot saved
- [ ] All work committed with issue IDs
- [ ] All 523 tests passing

---

## End of Day 1 Summary

**Time spent**: 7-12 hours
**Violations fixed**: 34 + 87 = 121 / 203 (60%)
**Commits**: 6-10 commits with issue IDs

**Verification**:
```bash
# Phase 1: No eval/exec
grep -r "eval\|exec" scripts/ agents/ apps/ libs/ --include="*.py"
# Expected: 0 results

# Phase 2: Determinism
bash /tmp/test_det.sh
# Expected: ✅ 3x identical

# Full test suite
pytest tests/ --cov
# Expected: 523/523 pass, ≥95% coverage
```

**Before leaving for Day 2**:
- [ ] Update ISSUE_TRACKER.md with Phase 1-2 complete
- [ ] Update this checklist with completion time
- [ ] Commit any remaining work: `git commit -m "docs(AV-001): End of Day 1 — Phase 1-2 complete"`
- [ ] Tag phase checkpoint: `git tag audit-phase2-complete-$(git rev-parse HEAD | cut -c1-7)`

---

## Day 2: Evidence + Posture (7-10 hours)

### Morning: Phase 3 — Evidence Parity + Rubric (4-6 hours)

**Objective**: Enforce evidence parity and rubric compliance

**Task 3.1: Rubric compliance enforcement** (90 min)
- [ ] Review RubricScorer in agents/scoring/rubric_scorer.py
- [ ] Verify MIN_QUOTES_PER_THEME = 2 is enforced
- [ ] Test with real ESG data: `pytest tests/scoring/ -k rubric -v`
- [ ] Fix any non-compliant evidence records
- [ ] Commit: `git commit -m "fix(AV-001-E01): Enforce 2+ quotes in rubric scoring"`

**Task 3.2: Parity validation** (90 min)
- [ ] Review ParityChecker in libs/retrieval/parity_checker.py
- [ ] Verify evidence ⊆ retrieval invariant enforced
- [ ] Test with realistic fusion: `pytest tests/retrieval/ -k parity -v`
- [ ] Add checks for missing evidence
- [ ] Commit: `git commit -m "fix(AV-001-E02): Enforce parity validation"`

**Task 3.3: Evidence contract validation** (60 min)
- [ ] Review evidence record structure (extract_30w, doc_id, etc.)
- [ ] Verify all evidence records have required fields
- [ ] Test with real company reports (Apple, Microsoft)
- [ ] Fix any missing field issues
- [ ] Commit: `git commit -m "fix(AV-001-E03): Validate evidence contract"`

**Task 3.4: Phase 3 audit** (10 min)
```bash
# Audit after Phase 3
python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase3.json

# Verify evidence violations fixed
grep '"type": "EVIDENCE"' artifacts/audit_after_phase3.json | wc -l
# Expected: 0-5 (may fix some posture issues too)

# Run tests
pytest tests/ --cov
# Expected: 523/523 pass
```

**End of Morning (Phase 3) Checklist**:
- [ ] Rubric compliance enforced (≥2 quotes)
- [ ] Parity validation active (evidence ⊆ top-k)
- [ ] Evidence contract validated
- [ ] Phase 3 audit snapshot saved
- [ ] All 523 tests passing

---

### Afternoon: Phase 4 — Production Posture (3-4 hours)

**Objective**: Fix type safety, error handling, Docker compliance

**Task 4.1: Type safety (mypy --strict)** (60 min)
```bash
# Run mypy on all CP files
mypy --strict apps/ agents/ libs/ scripts/ > /tmp/mypy_output.txt 2>&1
wc -l /tmp/mypy_output.txt
# Expected: ≤10 errors (from Phase 4 priority issues)
```

- [ ] Fix type annotation errors (add type hints where missing)
- [ ] Add Optional where needed
- [ ] Fix return type annotations
- [ ] Test: `mypy --strict` = 0 errors
- [ ] Commit: `git commit -m "fix(AV-001-P01): Fix type safety (mypy --strict)"`

**Task 4.2: Error handling** (60 min)
- [ ] Review error handling in API endpoints (apps/api/main.py)
- [ ] Add missing try/except blocks for file I/O
- [ ] Add error responses for invalid JSON parsing
- [ ] Test error cases: `pytest tests/api/ -k error -v`
- [ ] Commit: `git commit -m "fix(AV-001-P02): Add error handling to API endpoints"`

**Task 4.3: Docker offline validation** (30 min)
```bash
# Verify no external network calls
docker run --network none esg-scorer /trace
# Expected: 200 OK, gate verdicts returned

# Check code for network calls
grep -r "requests\|urllib\|socket" apps/ agents/ libs/ --include="*.py" \
  | grep -v "# mock\|Mock\|test" | wc -l
# Expected: 0 (or only in test/mock code)
```

- [ ] Remove any `requests.get()` or similar (use MockHTTPClient)
- [ ] Verify /trace endpoint is read-only (no side effects)
- [ ] Test Docker offline deployment
- [ ] Commit: `git commit -m "fix(AV-001-P03): Ensure Docker offline compliance"`

**Task 4.4: Phase 4 audit** (10 min)
```bash
# Audit after Phase 4
python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase4.json

# Verify posture violations fixed
grep '"type": "POSTURE"' artifacts/audit_after_phase4.json | wc -l
# Expected: 0-3

# Run full test suite
pytest tests/ --cov
# Expected: 523/523 pass
```

**End of Afternoon (Phase 4) Checklist**:
- [ ] Type safety = 0 errors (mypy --strict)
- [ ] Error handling complete
- [ ] Docker offline test passes
- [ ] Phase 4 audit snapshot saved
- [ ] All 523 tests passing

---

## End of Day 2 Summary

**Time spent**: 7-10 hours
**Violations fixed so far**: 121 + 29 + 12 = 162 / 203 (80%)
**Commits**: 6-8 commits with issue IDs

**Before leaving for Day 3**:
- [ ] Update ISSUE_TRACKER.md with Phase 3-4 complete
- [ ] Commit status: `git commit -m "docs(AV-001): End of Day 2 — Phase 3-4 complete"`
- [ ] Tag phase checkpoint: `git tag audit-phase4-complete-$(git rev-parse HEAD | cut -c1-7)`

---

## Day 3: Errors + Verification (3-6 hours)

### Morning: Phase 5 — Error Handling & Logging (2-3 hours)

**Objective**: Catch all silent failures, add comprehensive logging

**Task 5.1: Silent failure detection** (60 min)
```bash
# Find all except handlers
grep -rn "except" scripts/ agents/ apps/ libs/ --include="*.py" \
  | grep -v "pytest\|Mock\|test" > /tmp/except_handlers.txt
wc -l /tmp/except_handlers.txt
# Expected: ~100+ except blocks

# Check for silenced exceptions (except: pass)
grep -rn "except.*:$" scripts/ agents/ apps/ libs/ --include="*.py" \
  | head -20
# Each should be reviewed (some OK if documented)
```

- [ ] Add logging to all exception handlers
- [ ] Ensure exceptions are re-raised or result in clear error response
- [ ] Add failure tests: `pytest tests/ -k error -v`
- [ ] Commit: `git commit -m "fix(AV-001-E01): Add comprehensive error logging"`

**Task 5.2: Phase 5 audit** (10 min)
```bash
# Audit after Phase 5
python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase5.json

# Verify error violations fixed
grep '"type": "ERRORS"' artifacts/audit_after_phase5.json | wc -l
# Expected: 0-10 (some error-handling issues may remain, covered in Phase 6)

# Run tests
pytest tests/ --cov
# Expected: 523/523 pass
```

**End of Morning Checklist**:
- [ ] Error handling comprehensive
- [ ] Logging added to critical paths
- [ ] Phase 5 audit snapshot saved
- [ ] All 523 tests passing

---

### Afternoon: Phase 6 — Final Verification & Sign-Off (2-3 hours)

**Objective**: Zero violations, all gates passing, production ready

**Task 6.1: Run final audit** (5 min)
```bash
# Complete audit run
python scripts/qa/authenticity_audit.py > artifacts/audit_final.json

# Parse results
python -c "
import json
with open('artifacts/audit_final.json') as f:
    data = json.load(f)
print(f'Total violations: {len(data)}')
print(f'FATAL violations: {sum(1 for v in data if v.get(\"severity\") == 0)}')
"
# Expected: Total = 0, FATAL = 0
```

- [ ] Verify audit shows 0 violations
- [ ] If violations remain, go back to relevant phase
- [ ] Audit report saved to artifacts/

**Task 6.2: Full test suite with coverage** (30 min)
```bash
# Run full suite with coverage
pytest tests/ --cov=scripts,agents,apps,libs --cov-report=html,term-missing

# Check coverage
grep "TOTAL" .coverage | grep -oP '\d+%$'
# Expected: ≥95%
```

- [ ] All 523 tests passing
- [ ] Coverage ≥95% on modified files
- [ ] No regressions detected

**Task 6.3: Type safety verification** (5 min)
```bash
mypy --strict scripts/ agents/ apps/ libs/
# Expected: 0 errors
```

- [ ] mypy --strict passes
- [ ] No type errors remaining

**Task 6.4: Determinism final check** (10 min)
```bash
# Final 3x run verification
bash /tmp/test_det.sh
# Expected: ✅ All 3 hashes identical
```

- [ ] Determinism verified (byte-identical)
- [ ] Reproducibility confirmed

**Task 6.5: Docker offline final check** (5 min)
```bash
docker run --network none esg-scorer /trace
# Expected: 200 OK, all gates in response
```

- [ ] Docker deployment works offline
- [ ] /trace endpoint returns full gate verdicts

**Task 6.6: Create completion report** (30 min)
- [ ] Generate COMPLETION_REPORT.md with:
  - Final violation counts (0)
  - Test results (523/523 pass)
  - Coverage metrics (≥95%)
  - Determinism verification (3x identical)
  - Timeline summary (actual time spent)
  - Sign-off statement
- [ ] Save to artifacts/COMPLETION_REPORT.md
- [ ] Commit: `git commit -m "docs(AV-001): Completion report — all 203 violations resolved"`

**Task 6.7: Tag and sign off** (5 min)
```bash
# Create final tag
git tag -a v1.0.0-audit-clean -m "AV-001 Complete — All 203 violations resolved"

# Create final commit
git commit -m "chore(AV-001): Final sign-off — production ready"
```

- [ ] Final commit tagged as v1.0.0-audit-clean
- [ ] Completion marked in ISSUE_TRACKER.md
- [ ] All work pushed to repository

**End of Day 3 Checklist**:
- [ ] Audit = 0 violations
- [ ] 523/523 tests passing, ≥95% coverage
- [ ] mypy --strict = 0 errors
- [ ] Determinism verified (3x runs)
- [ ] Docker offline works
- [ ] Completion report generated
- [ ] All work tagged and committed

---

## Final Status

```
✅ Phase 1 (FATAL):      34/34 violations fixed ✅
✅ Phase 2 (Determinism): 87/87 violations fixed ✅
✅ Phase 3 (Evidence):    29/29 violations fixed ✅
✅ Phase 4 (Posture):     12/12 violations fixed ✅
✅ Phase 5 (Errors):      74/74 violations fixed ✅
✅ Phase 6 (Verification): Complete ✅
────────────────────────────────────────────────
✅ TOTAL:               203/203 violations resolved ✅

Status: 🚀 PRODUCTION READY
```

---

## Time Tracking

| Phase | Estimated | Actual | Notes |
|-------|-----------|--------|-------|
| Phase 1 | 4-7h | ___ h | FATAL removal |
| Phase 2 | 3-5h | ___ h | Determinism |
| Phase 3 | 4-6h | ___ h | Evidence parity |
| Phase 4 | 3-4h | ___ h | Production posture |
| Phase 5 | 2-3h | ___ h | Error handling |
| Phase 6 | 2-3h | ___ h | Verification |
| **TOTAL** | **18-28.5h** | **___ h** | **Full remediation** |

---

## Quick Reference Commands

```bash
# Baseline audit (Phase 0)
python scripts/qa/authenticity_audit.py > artifacts/audit_baseline.json

# Check violations remaining
grep -c "violation_id" artifacts/audit_current.json

# Check for eval/exec
grep -r "eval\|exec" scripts/ agents/ apps/ libs/ --include="*.py" | wc -l

# Test after changes
pytest tests/ --cov

# Type check
mypy --strict scripts/ agents/ apps/ libs/

# Determinism test (3x runs)
export FIXED_TIME=1729000000.0 SEED=42
bash /tmp/test_det.sh

# Commit with issue ID
git commit -m "fix(AV-001-F001): Description"

# Create checkpoint tag
git tag audit-phaseN-complete-$(git rev-parse HEAD | cut -c1-7)

# Emergency rollback
git reset --hard audit-baseline-20251026
```

---

## Document Info

**Title**: AV-001 Quick Start Checklist
**Version**: 1.0
**Created**: 2025-10-26
**Protocol**: SCA v13.8-MEA
**Target Completion**: 2025-10-29

---

**Ready to start? Begin with Day 1 morning tasks above.** 🚀
