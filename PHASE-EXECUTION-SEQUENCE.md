# AV-001 Phase Execution Sequence — Complete Roadmap

**Current Status**: Scaffolding complete, Phase 0 ready to execute
**Start Date**: 2025-10-27 (Day 1)
**End Date**: 2025-10-29 (Day 3)
**Total Duration**: 14-22 hours

---

## What Comes Next: Complete Execution Plan

Based on the AV-001 remediation plan, here is the **complete sequence of phases** that should be executed:

---

## Phase 0: Pre-Remediation Setup ✅ → NOW (5 minutes)

**Status**: Ready to execute immediately
**Duration**: 5 minutes (before Phase 1)
**Blocking**: Required before Phase 1 can start

### Three Setup Commands:

#### Command 0.1: Create Immutable Baseline Snapshot
```bash
cd "C:\projects\Work Projects\ibm-projects\ESG Evaluation\prospecting-engine"
git tag -a audit-baseline-20251026 -m "AV-001 pre-remediation baseline snapshot"
```
**Purpose**: Emergency rollback capability if phases fail
**Success**: `git tag -l | grep audit-baseline-20251026` shows the tag

#### Command 0.2: Capture Baseline Violation Count
```bash
python scripts/qa/authenticity_audit.py > artifacts/audit_baseline.json

# Verify
python -c "import json; data = json.load(open('artifacts/audit_baseline.json')); print(f'Violations: {len(data)}')"
```
**Purpose**: Baseline for comparison after each phase
**Success**: Output shows exactly **203 violations**

#### Command 0.3: Verify All Tests Currently Pass
```bash
pytest tests/ --cov -q
```
**Purpose**: Establish that no regressions already exist
**Success**: Output shows **523 passed**

### Phase 0 Completion Check:
- [ ] Baseline tag created
- [ ] Baseline audit = 203 violations
- [ ] All tests = 523 passing
- [ ] Ready for Phase 1

---

## Phase 1: Remove eval() and exec() 📋 → DAY 1 MORNING (4-7 hours)

**Status**: Queued after Phase 0
**Duration**: 4-7 hours
**Violations to Fix**: 34 FATAL issues (F001-F034)
**Blocking**: Everything else (Phase 1 must complete before Phase 2)

### What You'll Do:
1. **Find all eval() instances** (15 min)
   - Grep: `grep -rn "eval(" scripts/ agents/ apps/ libs/ --include="*.py"`
   - Expected: ~17-20 instances

2. **Find all exec() instances** (15 min)
   - Grep: `grep -rn "exec(" scripts/ agents/ apps/ libs/ --include="*.py"`
   - Expected: ~14-17 instances

3. **Apply fixes in batches** (3-4 hours)
   - For each eval/exec, apply appropriate fix pattern from REMEDIATION_PLAN.md
   - Pattern 1A: eval(JSON) → json.loads()
   - Pattern 1B: eval(math) → ast.literal_eval()
   - Pattern 1C: exec(code) → direct function call
   - Test after each fix: `pytest tests/ --cov -q`
   - Commit with issue ID: `git commit -m "fix(AV-001-F001): Remove eval() in file.py"`

4. **Verify Phase 1 Complete** (10 min)
   ```bash
   grep -r "eval\|exec" scripts/ agents/ apps/ libs/ --include="*.py" | wc -l
   # MUST show: 0

   python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase1.json
   # MUST show: FATAL violations = 0
   ```

### Phase 1 Success Criteria:
- ✅ 0 eval() or exec() calls remaining
- ✅ 0 FATAL violations in audit
- ✅ 523 tests still passing
- ✅ Violations reduced: 203 → 169 (34 fixed)

### Phase 1 Documents:
- **Daily checklist**: QUICK_START_CHECKLIST.md (Day 1 morning)
- **Code examples**: REMEDIATION_PLAN.md (Phase 1)
- **Progress tracking**: ISSUE_TRACKER.md (Priority 0 section)

### When Phase 1 is Done:
→ **Proceed to Phase 2**

---

## Phase 2: Determinism — Seed All Randomness 🎲 → DAY 1 AFTERNOON (3-5 hours)

**Status**: Queued after Phase 1 completion
**Duration**: 3-5 hours
**Violations to Fix**: 87 Determinism issues (D001-D087)
**Blocking**: Phase 3 (depends on deterministic execution)

### What You'll Do:
1. **Find unseeded randomness** (15 min)
   - Grep: `grep -rn "random\." scripts/ agents/ apps/ libs/ --include="*.py"`
   - Grep: `grep -rn "np\.random\|numpy\.random" scripts/ agents/ apps/ libs/ --include="*.py"`
   - Expected: ~80-95 instances

2. **Find non-deterministic time** (15 min)
   - Grep: `grep -rn "datetime\.now\|time\.time" scripts/ agents/ apps/ libs/ --include="*.py"`
   - Expected: ~15-20 instances

3. **Apply seeding fixes** (2-3 hours)
   - For each module, add: `from libs.utils.determinism import initialize_numpy_seed, get_seeded_random`
   - Call: `initialize_numpy_seed()` once per module
   - Replace time calls with: `from libs.utils.clock import get_clock`
   - Replace random calls with: `get_seeded_random()`
   - Test after each module: `pytest tests/ -k <module>`

4. **Verify Determinism** (30-60 min)
   ```bash
   export FIXED_TIME=1729000000.0 SEED=42 PYTHONHASHSEED=0
   bash /tmp/test_det.sh
   # MUST output: ✅ DETERMINISM VERIFIED: All 3 runs identical
   ```

5. **Verify Phase 2 Complete**
   ```bash
   python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase2.json
   # MUST show: Determinism violations near 0

   pytest tests/ --cov -q
   # MUST show: 523 passed
   ```

### Phase 2 Success Criteria:
- ✅ 3x identical runs (byte-identical SHA256 hashes)
- ✅ 87 determinism violations fixed
- ✅ 523 tests still passing
- ✅ Violations reduced: 169 → 82

### Phase 2 Documents:
- **Daily checklist**: QUICK_START_CHECKLIST.md (Day 1 afternoon)
- **Code examples**: REMEDIATION_PLAN.md (Phase 2)
- **Progress tracking**: ISSUE_TRACKER.md (Priority 1 section)

### When Phase 2 is Done (End of Day 1):
- ✅ Tag checkpoint: `git tag audit-phase2-complete-$(git rev-parse HEAD | cut -c1-7)`
- ✅ Commit summary: `git commit -m "docs(AV-001): Phase 1-2 complete — 121/203 violations fixed"`
- → **Proceed to Day 2, Phase 3**

---

## Phase 3: Evidence Parity & Rubric Compliance 📊 → DAY 2 MORNING (4-6 hours)

**Status**: Queued after Phase 2 completion
**Duration**: 4-6 hours
**Violations to Fix**: 29 Evidence issues (E001-E029)
**Blocking**: Phase 4 (regulatory compliance required)

### What You'll Do:
1. **Enforce Rubric MIN_QUOTES** (90 min)
   - Edit: `agents/scoring/rubric_scorer.py`
   - Add: `MIN_QUOTES_PER_THEME = 2`
   - Enforce: If evidence < 2 quotes → stage 0
   - Test: `pytest tests/scoring/ -k rubric -v`

2. **Implement Parity Validation** (90 min)
   - Use: `libs/retrieval/parity_checker.py`
   - Enforce: `evidence_ids ⊆ fused_top_k_ids`
   - Test: `pytest tests/retrieval/ -k parity -v`

3. **Validate Evidence Contract** (60 min)
   - Required fields: extract_30w, doc_id, theme_code
   - Add schema validation
   - Test with real ESG data (Apple, Microsoft reports)

4. **Verify Phase 3 Complete**
   ```bash
   python scripts/qa/verify_parity.py
   # MUST output: PASS

   python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase3.json
   # MUST show: Evidence violations = 0

   pytest tests/ --cov -q
   # MUST show: 523 passed
   ```

### Phase 3 Success Criteria:
- ✅ Parity validation: PASS (evidence ⊆ retrieval)
- ✅ Rubric compliance: MIN_QUOTES = 2 enforced
- ✅ 29 evidence violations fixed
- ✅ 523 tests still passing
- ✅ Violations reduced: 82 → 53

### Phase 3 Documents:
- **Daily checklist**: QUICK_START_CHECKLIST.md (Day 2 morning)
- **Code examples**: REMEDIATION_PLAN.md (Phase 3)
- **Progress tracking**: ISSUE_TRACKER.md (Priority 2 section)

### When Phase 3 is Done:
→ **Proceed to Phase 4 (same day afternoon)**

---

## Phase 4: Production Posture ✅ → DAY 2 AFTERNOON (3-4 hours)

**Status**: Queued after Phase 3 completion
**Duration**: 3-4 hours
**Violations to Fix**: 12 Posture issues (P001-P012)
**Blocking**: Phase 5 (production readiness)

### What You'll Do:
1. **Fix Type Safety** (60 min)
   - Run: `mypy --strict apps/ agents/ libs/ scripts/`
   - Add type annotations to functions
   - Fix Optional and Union types
   - Target: 0 mypy errors

2. **Add Error Handling** (60 min)
   - Add try/except to API endpoints
   - Add error responses (404, 500 status codes)
   - Add logging in exception handlers
   - Test: `pytest tests/api/ -k error -v`

3. **Verify Docker Compliance** (30 min)
   ```bash
   docker run --network none esg-scorer /trace
   # MUST return: 200 OK with gate verdicts
   ```

4. **Verify Phase 4 Complete**
   ```bash
   mypy --strict apps/ agents/ libs/ scripts/
   # MUST output: 0 errors

   python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase4.json
   # MUST show: Posture violations = 0

   pytest tests/ --cov -q
   # MUST show: 523 passed
   ```

### Phase 4 Success Criteria:
- ✅ mypy --strict: 0 errors
- ✅ Docker offline: working (no network calls)
- ✅ 12 posture violations fixed
- ✅ 523 tests still passing
- ✅ Violations reduced: 53 → 41

### Phase 4 Documents:
- **Daily checklist**: QUICK_START_CHECKLIST.md (Day 2 afternoon)
- **Code examples**: REMEDIATION_PLAN.md (Phase 4)
- **Progress tracking**: ISSUE_TRACKER.md (Priority 3 section)

### When Phase 4 is Done (End of Day 2):
- ✅ Tag checkpoint: `git tag audit-phase4-complete-$(git rev-parse HEAD | cut -c1-7)`
- ✅ Commit summary: `git commit -m "docs(AV-001): Phase 3-4 complete — 162/203 violations fixed"`
- → **Proceed to Day 3, Phase 5**

---

## Phase 5: Error Handling & Logging 🛡️ → DAY 3 MORNING (2-3 hours)

**Status**: Queued after Phase 4 completion
**Duration**: 2-3 hours
**Violations to Fix**: 74 Error issues (ERR001-ERR074)
**Blocking**: Phase 6 (final gates)

### What You'll Do:
1. **Find Silent Failures** (30 min)
   - Grep: `grep -rn "except.*:" scripts/ agents/ apps/ libs/ --include="*.py"`
   - Check for `except: pass` patterns (silent failures)
   - Expected: ~100+ except blocks to review

2. **Add Logging** (60 min)
   - Add logger to each module
   - Log every exception: `logger.error(f"Error: {e}")`
   - Ensure exceptions are re-raised (not silenced)
   - Add info/warning logs at critical points

3. **Verify Phase 5 Complete**
   ```bash
   pytest tests/ -k error -v
   # MUST output: All pass

   pytest tests/ --cov=agents,apps,libs --cov-report=term | grep TOTAL
   # MUST show: ≥95% coverage

   python scripts/qa/authenticity_audit.py > artifacts/audit_after_phase5.json
   # MUST show: Error violations = 0

   pytest tests/ --cov -q
   # MUST show: 523 passed
   ```

### Phase 5 Success Criteria:
- ✅ Error handling: comprehensive
- ✅ Logging: added to critical paths
- ✅ 74 error violations fixed
- ✅ Coverage: ≥95%
- ✅ 523 tests still passing
- ✅ Violations reduced: 41 → 0 (all fixed!)

### Phase 5 Documents:
- **Daily checklist**: QUICK_START_CHECKLIST.md (Day 3 morning)
- **Code examples**: REMEDIATION_PLAN.md (Phase 5)
- **Progress tracking**: ISSUE_TRACKER.md (Priority 4 section)

### When Phase 5 is Done:
→ **Proceed to Phase 6 (final verification)**

---

## Phase 6: Final Verification & Sign-Off 🚀 → DAY 3 AFTERNOON (2-3 hours)

**Status**: Queued after Phase 5 completion
**Duration**: 2-3 hours
**Violations to Fix**: 0 (verify all 203 fixed)
**Blocking**: None (final phase)

### What You'll Do:
1. **Run Complete Audit** (5 min)
   ```bash
   python scripts/qa/authenticity_audit.py > artifacts/audit_final.json

   python -c "import json; data = json.load(open('artifacts/audit_final.json')); print(f'Total violations: {len(data)}')"
   # MUST output: Total violations: 0
   ```

2. **Run Full Test Suite** (30 min)
   ```bash
   pytest tests/ --cov=agents,apps,libs --cov-report=html,term
   # MUST output: 523 passed, ≥95% coverage
   ```

3. **Verify Type Safety** (5 min)
   ```bash
   mypy --strict apps/ agents/ libs/ scripts/
   # MUST output: 0 errors
   ```

4. **Verify Determinism** (10 min)
   ```bash
   export FIXED_TIME=1729000000.0 SEED=42 PYTHONHASHSEED=0
   bash /tmp/test_det.sh
   # MUST output: ✅ DETERMINISM VERIFIED
   ```

5. **Verify Docker Offline** (5 min)
   ```bash
   docker run --network none esg-scorer /trace
   # MUST return: 200 OK
   ```

6. **Create Completion Report** (30 min)
   - Document all 203 violations fixed
   - Record timeline (actual hours per phase)
   - Record all test results
   - Sign off as complete

7. **Tag and Commit** (5 min)
   ```bash
   git add .
   git commit -m "chore(AV-001): Final commit — all 203 violations resolved"
   git tag -a v1.0.0-audit-clean -m "AV-001 Complete — Production Ready"
   git push origin v1.0.0-audit-clean
   ```

### Phase 6 Success Criteria:
- ✅ Audit: 0 violations
- ✅ Tests: 523/523 pass with ≥95% coverage
- ✅ Type safety: 0 errors
- ✅ Determinism: 3x identical
- ✅ Docker: offline working
- ✅ All gates: PASS
- ✅ Tagged: v1.0.0-audit-clean

### Phase 6 Documents:
- **Daily checklist**: QUICK_START_CHECKLIST.md (Day 3 afternoon)
- **Code examples**: REMEDIATION_PLAN.md (Phase 6)
- **Completion tracking**: ISSUE_TRACKER.md (Phase 6 section)

### When Phase 6 is Done (End of Day 3):
```
✅ ALL 203 VIOLATIONS RESOLVED
✅ ALL TESTS PASSING
✅ ALL GATES PASSING
✅ PRODUCTION READY 🚀
```

---

## Complete Timeline Summary

```
PHASE 0 (Setup):         5 min   → Baseline tag, audit capture, test verify
    ↓
PHASE 1 (FATAL):         4-7h    → Remove 34 eval/exec calls
    ↓
PHASE 2 (Determinism):   3-5h    → Seed 87 randomness operations
    ↓ [END OF DAY 1: 121/203 violations fixed]
PHASE 3 (Evidence):      4-6h    → Enforce 29 parity/rubric rules
    ↓
PHASE 4 (Posture):       3-4h    → Fix 12 production issues
    ↓ [END OF DAY 2: 162/203 violations fixed]
PHASE 5 (Errors):        2-3h    → Handle 74 silent failures
    ↓
PHASE 6 (Verification):  2-3h    → Verify 0 violations remain
    ↓ [END OF DAY 3: 203/203 violations fixed]

🚀 PRODUCTION READY
```

---

## Key Success Metrics

| Metric | Target | Phase to Verify |
|--------|--------|-----------------|
| Violations | 203 → 0 | Phase 6 |
| FATAL violations | 34 → 0 | Phase 1 |
| Determinism | 3x identical | Phase 2 |
| Tests passing | 523/523 | All phases |
| Type safety | 0 errors | Phase 4 |
| Coverage | ≥95% | Phase 5 |
| Docker offline | Working | Phase 4 |
| Final tag | v1.0.0-audit-clean | Phase 6 |

---

## Right Now: What to Do Immediately

### **Next 30 Minutes**:
1. Read `README.md` (10 min)
2. Read `EXECUTIVE_SUMMARY.md` (5 min)
3. Review Day 1 Morning in `QUICK_START_CHECKLIST.md` (5 min)
4. Execute Phase 0 setup commands (5 min)
5. Verify Phase 0 complete with checklist above

### **Then (Day 1 Morning)**:
Start Phase 1 using QUICK_START_CHECKLIST.md Day 1 Morning section

### **Total Path**:
Phase 0 (5 min) → Phase 1-2 (7-12h) → Phase 3-4 (7-10h) → Phase 5-6 (3-6h) = **14-22 hours total**

---

## Execution Safety Nets

### **If You Get Stuck** (>30 minutes):
→ Check TROUBLESHOOTING_GUIDE.md (symptom-based diagnosis)

### **If a Phase Fails**:
→ Use emergency rollback: `git reset --hard audit-baseline-20251026`

### **If Estimates Are Wrong**:
→ Day 3 afternoon has 3-6 hour buffer built in

### **If You Need to Pause**:
→ Commit current work, tag phase progress, resume next day

---

## The Big Picture

You are executing **6 sequential phases** to fix **203 authenticity violations** that make the ESG evaluation system:
- **Unsafe** (eval/exec security risk)
- **Non-reproducible** (unseeded randomness)
- **Non-compliant** (evidence not validated)
- **Non-production-ready** (error handling gaps)

After completion, the system will be:
- ✅ Safe (no eval/exec)
- ✅ Deterministic (3x identical runs)
- ✅ Compliant (evidence parity validated)
- ✅ Production-ready (all tests pass, type-safe, logged)

---

**Document**: AV-001 Complete Phase Execution Sequence
**Version**: 1.0
**Created**: 2025-10-26
**Status**: Ready to execute starting 2025-10-27

**Begin Phase 0 now. The path is clear.** 🚀
